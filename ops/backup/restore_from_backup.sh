#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
OPS_BACKUP_DIR="$SCRIPT_DIR"

BASE_DIR=""
DOCUMENTS_DIR=""
ASSETS_DIR=""
TEMPLATES_DIR=""
BACKUP_ROOT=""
BAC_ENV_FILE="$OPS_BACKUP_DIR/bac.env"
DB_ENV_FILE="$OPS_BACKUP_DIR/db.env"
MYSQL_IMAGE="mysql:8.0"
FORCE="0"
RESTORE_MYSQL="1"

RESTORE_CONTAINER_NAME=""
TEMP_ROOT=""

log() {
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  sh restore_from_backup.sh --base-dir <path> [options]

Required:
  --base-dir <path>         Target path for restored storage/ files

Optional:
  --documents-dir <path>    Target for meeting PDFs (backend/documents)
  --assets-dir <path>       Target for data/assets
  --templates-dir <path>    Target for data/templates
  --backup-root <path>      Backup root (defaults from bac.env BACKUP_TARGET_PATH)
  --bac-env-file <path>     Path to bac.env (default: ./bac.env)
  --db-env-file <path>      Path to db.env (default: ./db.env)
  --mysql-image <image>     Temporary image used for restore (default: mysql:8.0)
  --skip-mysql              Restore files only (no database import)
  --force                   Allow deleting existing content in target directories
  -h, --help                Show this message

Example:
  sh restore_from_backup.sh \
    --base-dir ../../backend/storage \
    --documents-dir ../../backend/documents \
    --assets-dir ../../data/assets \
    --templates-dir ../../data/templates \
    --force
EOF
}

require_command() {
  name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    fail "Required command not found: $name"
  fi
}

resolve_existing_file() {
  path="$1"
  if [ ! -f "$path" ]; then
    fail "File not found: $path"
  fi

  dir_part="$(dirname "$path")"
  file_part="$(basename "$path")"
  dir_abs="$(CDPATH= cd -- "$dir_part" && pwd)"
  printf '%s/%s\n' "$dir_abs" "$file_part"
}

resolve_existing_dir() {
  path="$1"
  if [ ! -d "$path" ]; then
    fail "Directory not found: $path"
  fi

  CDPATH= cd -- "$path" && pwd
}

resolve_path_allow_missing_leaf() {
  path="$1"

  if [ -d "$path" ]; then
    CDPATH= cd -- "$path" && pwd
    return
  fi

  parent="$(dirname "$path")"
  leaf="$(basename "$path")"
  mkdir -p "$parent"
  parent_abs="$(CDPATH= cd -- "$parent" && pwd)"
  printf '%s/%s\n' "$parent_abs" "$leaf"
}

read_env_value() {
  env_file="$1"
  key="$2"

  if [ ! -f "$env_file" ]; then
    return 1
  fi

  line="$(grep -E "^${key}=" "$env_file" | tail -n 1 || true)"
  if [ -z "$line" ]; then
    return 1
  fi

  value="${line#*=}"

  case "$value" in
    \"*\")
      value="${value#\"}"
      value="${value%\"}"
      ;;
    \'*\')
      value="${value#\'}"
      value="${value%\'}"
      ;;
  esac

  printf '%s' "$value"
}

dir_has_content() {
  path="$1"

  if [ ! -d "$path" ]; then
    return 1
  fi

  if find "$path" -mindepth 1 -maxdepth 1 | read -r _; then
    return 0
  fi

  return 1
}

assert_safe_cleanup_target() {
  path="$1"

  case "$path" in
    ''|/)
      fail "Refusing to clean unsafe directory path: $path"
      ;;
  esac
}

clean_directory_contents() {
  path="$1"
  assert_safe_cleanup_target "$path"

  if [ -d "$path" ]; then
    find "$path" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  fi
}

restic_has_snapshots() {
  repo_path="$1"

  snapshot_json="$(docker run --rm \
    --env-file "$BAC_ENV_FILE" \
    -v "$BACKUP_ROOT:/backup-root:ro" \
    restic/restic:0.18.1 \
    -r "$repo_path" snapshots --json 2>/dev/null || true)"

  compact_json="$(printf '%s' "$snapshot_json" | tr -d '[:space:]')"

  if [ -z "$compact_json" ] || [ "$compact_json" = "[]" ]; then
    return 1
  fi

  return 0
}

restore_latest_snapshot() {
  repo_path="$1"
  target_dir="$2"

  docker run --rm \
    --env-file "$BAC_ENV_FILE" \
    -v "$BACKUP_ROOT:/backup-root:ro" \
    -v "$target_dir:/restore-target" \
    restic/restic:0.18.1 \
    -r "$repo_path" restore latest --target /restore-target
}

find_restored_leaf() {
  root="$1"
  leaf_pattern="$2"
  find "$root" -type d -path "$leaf_pattern" | head -n 1 || true
}

wait_for_mysql() {
  attempts="0"
  max_attempts="120"

  while [ "$attempts" -lt "$max_attempts" ]; do
    if docker exec \
      -e MYSQL_PWD="$MYSQL_PASSWORD" \
      "$RESTORE_CONTAINER_NAME" \
      mysqladmin ping -h 127.0.0.1 -u"$MYSQL_USER" --silent >/dev/null 2>&1; then
      return 0
    fi

    attempts=$((attempts + 1))
    sleep 1
  done

  return 1
}

cleanup() {
  if [ -n "$RESTORE_CONTAINER_NAME" ]; then
    docker stop "$RESTORE_CONTAINER_NAME" >/dev/null 2>&1 || true
  fi

  if [ -n "$TEMP_ROOT" ] && [ -d "$TEMP_ROOT" ]; then
    rm -rf "$TEMP_ROOT"
  fi
}

trap cleanup EXIT INT TERM

while [ $# -gt 0 ]; do
  case "$1" in
    --base-dir)
      [ $# -ge 2 ] || fail "Missing value for --base-dir"
      BASE_DIR="$2"
      shift 2
      ;;
    --documents-dir)
      [ $# -ge 2 ] || fail "Missing value for --documents-dir"
      DOCUMENTS_DIR="$2"
      shift 2
      ;;
    --assets-dir)
      [ $# -ge 2 ] || fail "Missing value for --assets-dir"
      ASSETS_DIR="$2"
      shift 2
      ;;
    --templates-dir)
      [ $# -ge 2 ] || fail "Missing value for --templates-dir"
      TEMPLATES_DIR="$2"
      shift 2
      ;;
    --backup-root)
      [ $# -ge 2 ] || fail "Missing value for --backup-root"
      BACKUP_ROOT="$2"
      shift 2
      ;;
    --bac-env-file)
      [ $# -ge 2 ] || fail "Missing value for --bac-env-file"
      BAC_ENV_FILE="$2"
      shift 2
      ;;
    --db-env-file)
      [ $# -ge 2 ] || fail "Missing value for --db-env-file"
      DB_ENV_FILE="$2"
      shift 2
      ;;
    --mysql-image)
      [ $# -ge 2 ] || fail "Missing value for --mysql-image"
      MYSQL_IMAGE="$2"
      shift 2
      ;;
    --skip-mysql)
      RESTORE_MYSQL="0"
      shift
      ;;
    --force)
      FORCE="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

[ -n "$BASE_DIR" ] || fail "Missing required argument: --base-dir"

require_command docker
require_command grep
require_command tail
require_command tr
require_command find
require_command mktemp
require_command cp
require_command rm
require_command head

BAC_ENV_FILE="$(resolve_existing_file "$BAC_ENV_FILE")"
DB_ENV_FILE="$(resolve_existing_file "$DB_ENV_FILE")"

if [ -z "$BACKUP_ROOT" ]; then
  BACKUP_ROOT="$(read_env_value "$BAC_ENV_FILE" "BACKUP_TARGET_PATH" || true)"
fi

if [ -z "$BACKUP_ROOT" ]; then
  BACKUP_ROOT="$OPS_BACKUP_DIR/../../backup-data"
fi

BACKUP_ROOT="$(resolve_existing_dir "$BACKUP_ROOT")"
BASE_DIR="$(resolve_path_allow_missing_leaf "$BASE_DIR")"

MYSQL_USER="$(read_env_value "$DB_ENV_FILE" "MYSQL_USER" || true)"
MYSQL_PASSWORD="$(read_env_value "$DB_ENV_FILE" "MYSQL_PASSWORD" || true)"
MYSQL_DATABASE="$(read_env_value "$DB_ENV_FILE" "MYSQL_DATABASE" || true)"
MYSQL_ROOT_PASSWORD="$(read_env_value "$DB_ENV_FILE" "MYSQL_ROOT_PASSWORD" || true)"

if [ -z "$MYSQL_USER" ]; then
  MYSQL_USER="portal_user"
fi

if [ -z "$MYSQL_DATABASE" ]; then
  MYSQL_DATABASE="ece_dept_portal"
fi

if [ -z "$MYSQL_PASSWORD" ]; then
  fail "MYSQL_PASSWORD is missing in $DB_ENV_FILE"
fi

if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
  MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD"
fi

prepare_target() {
  path="$1"
  label="$2"
  mkdir -p "$path"
  if dir_has_content "$path"; then
    if [ "$FORCE" != "1" ]; then
      fail "$label is not empty: $path (use --force to overwrite)"
    fi
    log "Cleaning existing $label contents: $path"
    clean_directory_contents "$path"
  fi
}

prepare_target "$BASE_DIR" "BASE_DIR"

if [ -n "$DOCUMENTS_DIR" ]; then
  DOCUMENTS_DIR="$(resolve_path_allow_missing_leaf "$DOCUMENTS_DIR")"
  prepare_target "$DOCUMENTS_DIR" "DOCUMENTS_DIR"
fi

if [ -n "$ASSETS_DIR" ]; then
  ASSETS_DIR="$(resolve_path_allow_missing_leaf "$ASSETS_DIR")"
  prepare_target "$ASSETS_DIR" "ASSETS_DIR"
fi

if [ -n "$TEMPLATES_DIR" ]; then
  TEMPLATES_DIR="$(resolve_path_allow_missing_leaf "$TEMPLATES_DIR")"
  prepare_target "$TEMPLATES_DIR" "TEMPLATES_DIR"
fi

if ! restic_has_snapshots "/backup-root/storage"; then
  fail "No snapshots found in storage backup repository."
fi

if [ "$RESTORE_MYSQL" = "1" ] && ! restic_has_snapshots "/backup-root/mysql"; then
  fail "No snapshots found in mysql logical backup repository."
fi

TEMP_ROOT="$(mktemp -d)"
STORAGE_RESTORE_DIR="$TEMP_ROOT/storage"
DOCUMENTS_RESTORE_DIR="$TEMP_ROOT/documents"
ASSETS_RESTORE_DIR="$TEMP_ROOT/assets"
TEMPLATES_RESTORE_DIR="$TEMP_ROOT/templates"
MYSQL_RESTORE_DIR="$TEMP_ROOT/mysql"
mkdir -p "$STORAGE_RESTORE_DIR" "$DOCUMENTS_RESTORE_DIR" "$ASSETS_RESTORE_DIR" "$TEMPLATES_RESTORE_DIR" "$MYSQL_RESTORE_DIR"

copy_restored_tree() {
  restore_root="$1"
  leaf_glob="$2"
  dest="$3"
  label="$4"

  restored_path="$(find_restored_leaf "$restore_root" "$leaf_glob")"
  [ -n "$restored_path" ] || fail "Could not locate restored $label directory in snapshot output."
  cp -a "$restored_path"/. "$dest"/
  log "$label restore completed: $dest"
}

log "Restoring latest storage snapshot"
restore_latest_snapshot "/backup-root/storage" "$STORAGE_RESTORE_DIR"
copy_restored_tree "$STORAGE_RESTORE_DIR" '*/source/storage' "$BASE_DIR" "Storage"

if [ -n "$DOCUMENTS_DIR" ] && restic_has_snapshots "/backup-root/documents"; then
  log "Restoring latest documents snapshot"
  restore_latest_snapshot "/backup-root/documents" "$DOCUMENTS_RESTORE_DIR"
  copy_restored_tree "$DOCUMENTS_RESTORE_DIR" '*/source/documents' "$DOCUMENTS_DIR" "Documents"
fi

if [ -n "$ASSETS_DIR" ] && restic_has_snapshots "/backup-root/assets"; then
  log "Restoring latest assets snapshot"
  restore_latest_snapshot "/backup-root/assets" "$ASSETS_RESTORE_DIR"
  copy_restored_tree "$ASSETS_RESTORE_DIR" '*/source/assets' "$ASSETS_DIR" "Assets"
fi

if [ -n "$TEMPLATES_DIR" ] && restic_has_snapshots "/backup-root/templates"; then
  log "Restoring latest templates snapshot"
  restore_latest_snapshot "/backup-root/templates" "$TEMPLATES_RESTORE_DIR"
  copy_restored_tree "$TEMPLATES_RESTORE_DIR" '*/source/templates' "$TEMPLATES_DIR" "Templates"
fi

if [ "$RESTORE_MYSQL" = "1" ]; then
  log "Restoring latest MySQL logical snapshot"
  restore_latest_snapshot "/backup-root/mysql" "$MYSQL_RESTORE_DIR"

  DATABASE_MAP_FILE="$(find "$MYSQL_RESTORE_DIR" -type f -name 'database_map.tsv' | head -n 1 || true)"
  [ -n "$DATABASE_MAP_FILE" ] || fail "database_map.tsv not found in restored MySQL logical backup."

  MYSQL_DUMP_CURRENT_DIR="$(dirname "$DATABASE_MAP_FILE")"
  DUMP_FILE="$(awk -F '\t' -v db="$MYSQL_DATABASE" '$1 == db { print $2; exit }' "$DATABASE_MAP_FILE" | tr -d '\r')"
  if [ -z "$DUMP_FILE" ]; then
    DUMP_FILE="$(awk -F '\t' 'NR==1 { print $2; exit }' "$DATABASE_MAP_FILE" | tr -d '\r')"
  fi
  [ -n "$DUMP_FILE" ] || fail "Could not resolve dump file from database_map.tsv"
  [ -f "$MYSQL_DUMP_CURRENT_DIR/$DUMP_FILE" ] || fail "Dump file missing: $DUMP_FILE"

  RESTORE_CONTAINER_NAME="ece-portal-restore-mysql-$$"
  log "Starting temporary MySQL container to import logical dump"

  docker run -d --rm \
    --name "$RESTORE_CONTAINER_NAME" \
    -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
    -e MYSQL_DATABASE="$MYSQL_DATABASE" \
    -e MYSQL_USER="$MYSQL_USER" \
    -e MYSQL_PASSWORD="$MYSQL_PASSWORD" \
    -v "$MYSQL_DUMP_CURRENT_DIR:/restore/current:ro" \
    "$MYSQL_IMAGE" >/dev/null

  if ! wait_for_mysql; then
    fail "Temporary MySQL container did not become ready in time."
  fi

  log "Importing database dump: $DUMP_FILE"
  docker exec \
    -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" \
    "$RESTORE_CONTAINER_NAME" \
    mysql -uroot -e "CREATE DATABASE IF NOT EXISTS \`$MYSQL_DATABASE\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

  docker exec -i \
    -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" \
    "$RESTORE_CONTAINER_NAME" \
    mysql -uroot < "$MYSQL_DUMP_CURRENT_DIR/$DUMP_FILE"

  OUT_SQL="$TEMP_ROOT/restored_${MYSQL_DATABASE}.sql"
  docker exec \
    -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" \
    "$RESTORE_CONTAINER_NAME" \
    mysqldump -uroot --single-transaction --routines --triggers --events --databases "$MYSQL_DATABASE" \
    > "$OUT_SQL"

  docker stop "$RESTORE_CONTAINER_NAME" >/dev/null 2>&1 || true
  RESTORE_CONTAINER_NAME=""

  RESTORE_SQL_OUT="$(CDPATH= cd -- "$OPS_BACKUP_DIR" && pwd)/restored_${MYSQL_DATABASE}.sql"
  cp "$OUT_SQL" "$RESTORE_SQL_OUT"
  log "MySQL logical dump validated and written to: $RESTORE_SQL_OUT"
  log "Import into the live portal DB with:"
  log "  docker compose --env-file .env.docker exec -T mysql mysql -u root -p\"\$MYSQL_ROOT_PASSWORD\" < $RESTORE_SQL_OUT"
fi

log "Restore finished successfully."
