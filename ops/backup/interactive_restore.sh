#!/usr/bin/env bash
# Interactive restore: pick a backup version by date/time, then restore.
#
# Usage (from ops/backup/):
#   ./interactive_restore.sh
#   ./interactive_restore.sh --force
#
# Shows 5 snapshots at a time (newest first). Enter 1-5 to restore that
# version, n/p to page newer/older, q to quit.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
BAC_ENV_FILE="$SCRIPT_DIR/bac.env"
PAGE_SIZE=5
FORCE_FLAG=""
LIST_REPO="/backup-root/storage"

usage() {
  cat <<'EOF'
Usage:
  ./interactive_restore.sh [--force] [--bac-env-file PATH] [--backup-root PATH]

Lists restic backup versions (from the storage repo) newest-first, five at a
time. Pick a number to restore that point in time across storage, documents,
assets, templates, and MySQL.

Options:
  --force             Overwrite non-empty target dirs (passed to restore script)
  --bac-env-file PATH Path to bac.env (default: ./bac.env)
  --backup-root PATH  Host backup root (default: BACKUP_TARGET_PATH in bac.env)
  -h, --help          Show this help
EOF
}

BACKUP_ROOT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --force)
      FORCE_FLAG="--force"
      shift
      ;;
    --bac-env-file)
      BAC_ENV_FILE="$2"
      shift 2
      ;;
    --backup-root)
      BACKUP_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ ! -f "$BAC_ENV_FILE" ]; then
  echo "ERROR: bac.env not found at $BAC_ENV_FILE" >&2
  echo "Copy bac.env.example → bac.env and set RESTIC_PASSWORD / BACKUP_TARGET_PATH." >&2
  exit 1
fi

read_env_value() {
  local env_file="$1" key="$2" line value
  line="$(grep -E "^${key}=" "$env_file" | tail -n 1 || true)"
  [ -n "$line" ] || return 1
  value="${line#*=}"
  case "$value" in
    \"*\") value="${value#\"}"; value="${value%\"}" ;;
    \'*\') value="${value#\'}"; value="${value%\'}" ;;
  esac
  printf '%s' "$value"
}

if [ -z "$BACKUP_ROOT" ]; then
  BACKUP_ROOT="$(read_env_value "$BAC_ENV_FILE" "BACKUP_TARGET_PATH" || true)"
fi
if [ -z "$BACKUP_ROOT" ]; then
  BACKUP_ROOT="$REPO_ROOT/backup-data"
fi

# Resolve relative BACKUP_TARGET_PATH against ops/backup (compose cwd).
case "$BACKUP_ROOT" in
  /*) ;;
  *)
    BACKUP_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR" && CDPATH= cd -- "$BACKUP_ROOT" && pwd)"
    ;;
esac

if [ ! -d "$BACKUP_ROOT" ]; then
  echo "ERROR: Backup root not found: $BACKUP_ROOT" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required to parse snapshot lists" >&2
  exit 1
fi

echo "Loading snapshots from $BACKUP_ROOT (storage repo)..."
SNAPSHOT_JSON="$(docker run --rm \
  --env-file "$BAC_ENV_FILE" \
  -v "$BACKUP_ROOT:/backup-root:ro" \
  restic/restic:0.18.1 \
  -r "$LIST_REPO" snapshots --json 2>/dev/null || true)"

if [ -z "$SNAPSHOT_JSON" ] || [ "$SNAPSHOT_JSON" = "[]" ]; then
  echo "ERROR: No snapshots found in storage repository." >&2
  echo "Confirm the backup service has completed at least one cycle." >&2
  exit 1
fi

# Build TSV: index(0-based)\tutc_time\tshort_id\tfull_id
SNAPSHOT_TSV="$(printf '%s' "$SNAPSHOT_JSON" | python3 -c '
import json, sys
snaps = json.load(sys.stdin)
snaps.sort(key=lambda s: s.get("time", ""), reverse=True)
for i, s in enumerate(snaps):
    time = (s.get("time") or "").replace("T", " ").replace("Z", " UTC")
    if "+" in time and " UTC" not in time:
        # keep offset times readable
        pass
    sid = s.get("short_id") or (s.get("id") or "")[:8]
    fid = s.get("id") or ""
    print(f"{i}\t{time}\t{sid}\t{fid}")
')"

TOTAL="$(printf '%s\n' "$SNAPSHOT_TSV" | grep -c . || true)"
if [ "$TOTAL" -lt 1 ]; then
  echo "ERROR: Could not parse snapshot list." >&2
  exit 1
fi

OFFSET=0
SELECTED_TIME=""
SELECTED_ID=""

page_end() {
  local end=$((OFFSET + PAGE_SIZE))
  if [ "$end" -gt "$TOTAL" ]; then
    end="$TOTAL"
  fi
  echo "$end"
}

show_page() {
  local end i line idx time sid num
  end="$(page_end)"
  echo
  echo "======================================================"
  echo " Backup versions (newest first)  —  showing $((OFFSET + 1))–${end} of ${TOTAL}"
  echo "======================================================"
  i=0
  while IFS= read -r line; do
    if [ "$i" -ge "$OFFSET" ] && [ "$i" -lt "$end" ]; then
      idx="$(printf '%s' "$line" | cut -f1)"
      time="$(printf '%s' "$line" | cut -f2)"
      sid="$(printf '%s' "$line" | cut -f3)"
      num=$((i - OFFSET + 1))
      printf "  %d)  %s   (id %s)\n" "$num" "$time" "$sid"
    fi
    i=$((i + 1))
  done <<EOF
$SNAPSHOT_TSV
EOF
  echo
  echo "  Enter 1-$(( end - OFFSET )) to restore that version"
  if [ "$end" -lt "$TOTAL" ]; then
    echo "  n  = older backups (next page)"
  fi
  if [ "$OFFSET" -gt 0 ]; then
    echo "  p  = newer backups (previous page)"
  fi
  echo "  q  = quit"
  echo
}

pick_line() {
  local want="$1" i=0 line
  while IFS= read -r line; do
    if [ "$i" -eq "$want" ]; then
      printf '%s\n' "$line"
      return 0
    fi
    i=$((i + 1))
  done <<EOF
$SNAPSHOT_TSV
EOF
  return 1
}

while true; do
  show_page
  end="$(page_end)"
  max_choice=$((end - OFFSET))
  printf "Choice: "
  read -r choice
  case "$choice" in
    q|Q)
      echo "Cancelled."
      exit 0
      ;;
    n|N)
      if [ "$end" -ge "$TOTAL" ]; then
        echo "Already at the oldest page."
      else
        OFFSET=$((OFFSET + PAGE_SIZE))
      fi
      ;;
    p|P)
      if [ "$OFFSET" -eq 0 ]; then
        echo "Already at the newest page."
      else
        OFFSET=$((OFFSET - PAGE_SIZE))
        if [ "$OFFSET" -lt 0 ]; then
          OFFSET=0
        fi
      fi
      ;;
    [1-9]|[1-9][0-9])
      if [ "$choice" -lt 1 ] || [ "$choice" -gt "$max_choice" ]; then
        echo "Invalid choice for this page (1–${max_choice})."
        continue
      fi
      abs_index=$((OFFSET + choice - 1))
      selected="$(pick_line "$abs_index")" || {
        echo "ERROR: Could not resolve selection." >&2
        exit 1
      }
      SELECTED_TIME="$(printf '%s' "$selected" | cut -f2)"
      # Prefer ISO time from restic: re-read from JSON by id for --as-of
      SELECTED_ID="$(printf '%s' "$selected" | cut -f4)"
      SELECTED_AS_OF="$(printf '%s' "$SNAPSHOT_JSON" | python3 -c '
import json,sys
want=sys.argv[1]
for s in json.load(sys.stdin):
    if s.get("id")==want or (s.get("short_id") or "").startswith(want[:8]):
        print(s.get("time",""))
        break
' "$SELECTED_ID")"
      echo
      echo "Selected: $SELECTED_TIME"
      echo "  snapshot id: $SELECTED_ID"
      echo "  as-of:       $SELECTED_AS_OF"
      echo
      printf "Restore this version to the portal data dirs? [y/N]: "
      read -r confirm
      case "$confirm" in
        y|Y|yes|YES)
          break
          ;;
        *)
          echo "Selection cancelled — pick again or q to quit."
          ;;
      esac
      ;;
    *)
      echo "Invalid input."
      ;;
  esac
done

echo
echo "Restoring backup as-of $SELECTED_AS_OF ..."
# shellcheck disable=SC2086
sh "$SCRIPT_DIR/restore_from_backup.sh" \
  --base-dir "$REPO_ROOT/backend/storage" \
  --documents-dir "$REPO_ROOT/backend/documents" \
  --assets-dir "$REPO_ROOT/data/assets" \
  --templates-dir "$REPO_ROOT/data/templates" \
  --backup-root "$BACKUP_ROOT" \
  --bac-env-file "$BAC_ENV_FILE" \
  --as-of "$SELECTED_AS_OF" \
  $FORCE_FLAG

echo
echo "Done. If MySQL was restored, import the SQL dump into the live DB:"
echo "  cd \"$REPO_ROOT\""
echo "  docker compose --env-file .env.docker exec -T mysql \\"
echo "    mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" < ops/backup/restored_ece_dept_portal.sql"
echo "  docker compose --env-file .env.docker exec backend alembic upgrade head"
