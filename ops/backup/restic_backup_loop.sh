#!/bin/sh
set -eu

log() {
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

require_command() {
  name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    log "ERROR: Required command is not available: $name"
    exit 1
  fi
}

validate_positive_integer() {
  value="$1"
  name="$2"

  case "$value" in
    ''|*[!0-9]*)
      log "ERROR: $name must be a positive integer. Current value: $value"
      exit 1
      ;;
  esac

  if [ "$value" -lt 1 ]; then
    log "ERROR: $name must be greater than or equal to 1. Current value: $value"
    exit 1
  fi
}

validate_port_number() {
  value="$1"
  name="$2"
  validate_positive_integer "$value" "$name"

  if [ "$value" -gt 65535 ]; then
    log "ERROR: $name must be less than or equal to 65535. Current value: $value"
    exit 1
  fi
}

: "${BACKUP_ROOT:=/backup-root}"
: "${STORAGE_SOURCE:=/source/storage}"
: "${DOCUMENTS_SOURCE:=/source/documents}"
: "${ASSETS_SOURCE:=/source/assets}"
: "${TEMPLATES_SOURCE:=/source/templates}"
: "${MYSQL_DUMP_ROOT:=${BACKUP_ROOT%/}/mysql-logical}"
: "${MYSQL_HOST:=mysql}"
: "${MYSQL_PORT:=3306}"
: "${MYSQL_USER:=portal_user}"
: "${MYSQL_DATABASE:=ece_dept_portal}"
: "${BACKUP_INTERVAL_DAYS:=1}"
: "${BACKUP_START_TIME:=23:00}"
: "${BACKUP_HOST_LABEL:=ece-portal}"

validate_positive_integer "$BACKUP_INTERVAL_DAYS" "BACKUP_INTERVAL_DAYS"
validate_port_number "$MYSQL_PORT" "MYSQL_PORT"

validate_time_hhmm() {
  value="$1"

  case "$value" in
    [0-2][0-9]:[0-5][0-9])
      ;;
    *)
      log "ERROR: BACKUP_START_TIME must be in HH:MM 24-hour format. Current value: $value"
      exit 1
      ;;
  esac

  hour="${value%:*}"
  if [ "$hour" -gt 23 ]; then
    log "ERROR: BACKUP_START_TIME hour must be between 00 and 23. Current value: $value"
    exit 1
  fi
}

to_number() {
  value="$1"
  value="${value#0}"
  if [ -z "$value" ]; then
    value="0"
  fi
  echo "$value"
}

seconds_until_start_time() {
  now_hour="$(to_number "$(date +%H)")"
  now_minute="$(to_number "$(date +%M)")"
  now_second="$(to_number "$(date +%S)")"

  now_total=$((now_hour * 3600 + now_minute * 60 + now_second))
  target_total=$((START_HOUR * 3600 + START_MINUTE * 60))

  if [ "$now_total" -le "$target_total" ]; then
    echo $((target_total - now_total))
    return
  fi

  echo $((24 * 3600 - (now_total - target_total)))
}

validate_time_hhmm "$BACKUP_START_TIME"
START_HOUR="$(to_number "${BACKUP_START_TIME%:*}")"
START_MINUTE="$(to_number "${BACKUP_START_TIME#*:}")"

require_command restic
require_command mysqldump
require_command mysql
require_command tr
require_command awk
require_command grep
require_command sed
require_command tail
require_command mktemp

resolve_restic_password() {
  if [ -n "${RESTIC_PASSWORD:-}" ]; then
    echo "$RESTIC_PASSWORD"
    return
  fi

  if [ -n "${BACKUP_ENCRYPTION_PASSWORD:-}" ]; then
    echo "$BACKUP_ENCRYPTION_PASSWORD"
    return
  fi

  log "ERROR: Set RESTIC_PASSWORD (preferred) or BACKUP_ENCRYPTION_PASSWORD in bac.env."
  exit 1
}

resolve_mysql_password() {
  if [ -n "${MYSQL_PASSWORD:-}" ]; then
    echo "$MYSQL_PASSWORD"
    return
  fi

  if [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
    echo "$MYSQL_ROOT_PASSWORD"
    return
  fi

  log "ERROR: Set MYSQL_PASSWORD (preferred) or MYSQL_ROOT_PASSWORD for logical MySQL backups."
  exit 1
}

RESTIC_PASSWORD_VALUE="$(resolve_restic_password)"
if [ -z "$RESTIC_PASSWORD_VALUE" ]; then
  log "ERROR: Resolved restic password is empty."
  exit 1
fi

MYSQL_PASSWORD_VALUE="$(resolve_mysql_password)"
if [ -z "$MYSQL_PASSWORD_VALUE" ]; then
  log "ERROR: Resolved MySQL password is empty."
  exit 1
fi

export RESTIC_PASSWORD="$RESTIC_PASSWORD_VALUE"
export MYSQL_PWD="$MYSQL_PASSWORD_VALUE"

STORAGE_REPO="${BACKUP_ROOT%/}/storage"
DOCUMENTS_REPO="${BACKUP_ROOT%/}/documents"
ASSETS_REPO="${BACKUP_ROOT%/}/assets"
TEMPLATES_REPO="${BACKUP_ROOT%/}/templates"
MYSQL_REPO="${BACKUP_ROOT%/}/mysql"
MYSQL_DUMP_CURRENT="${MYSQL_DUMP_ROOT%/}/current"
MYSQL_DUMP_STAGING="${MYSQL_DUMP_ROOT%/}/staging"
BACKUP_LOG_DIR="${BACKUP_ROOT%/}/logs"
BACKUP_LOG_FILE="${BACKUP_LOG_DIR%/}/backup_activity.csv"

LAST_DATA_ADDED_MB="0.000"
LAST_DATA_REMOVED_MB="0.000"
LAST_DIRS_ADDED="0"
LAST_DIRS_REMOVED="0"
LAST_FILES_ADDED="0"
LAST_FILES_REMOVED="0"

set_last_metrics_zero() {
  LAST_DATA_ADDED_MB="0.000"
  LAST_DATA_REMOVED_MB="0.000"
  LAST_DIRS_ADDED="0"
  LAST_DIRS_REMOVED="0"
  LAST_FILES_ADDED="0"
  LAST_FILES_REMOVED="0"
}

normalize_integer() {
  value="$1"
  value="$(printf '%s' "$value" | tr -d ',')"

  case "$value" in
    ''|*[!0-9]*)
      echo "0"
      ;;
    *)
      echo "$value"
      ;;
  esac
}

normalize_decimal() {
  value="$1"
  value="$(printf '%s' "$value" | tr -d ',')"

  case "$value" in
    ''|*[!0-9.]*|*.*.*)
      echo "0"
      ;;
    *)
      echo "$value"
      ;;
  esac
}

size_to_mb() {
  raw_value="$(normalize_decimal "$1")"
  size_unit="$2"

  awk -v value="$raw_value" -v unit="$size_unit" '
    BEGIN {
      factor = 0

      if (unit == "B") factor = 1 / (1024 * 1024)
      else if (unit == "KiB") factor = 1 / 1024
      else if (unit == "MiB") factor = 1
      else if (unit == "GiB") factor = 1024
      else if (unit == "TiB") factor = 1024 * 1024
      else if (unit == "kB") factor = 1000 / (1024 * 1024)
      else if (unit == "MB") factor = 1000000 / (1024 * 1024)
      else if (unit == "GB") factor = 1000000000 / (1024 * 1024)
      else factor = 0

      printf "%.3f", value * factor
    }
  '
}

size_pair_to_mb() {
  size_pair="$1"
  set -- $size_pair
  size_value="${1:-0}"
  size_unit="${2:-B}"
  size_to_mb "$size_value" "$size_unit"
}

sum_mb() {
  left_mb="$1"
  right_mb="$2"
  awk -v left="$left_mb" -v right="$right_mb" 'BEGIN { printf "%.3f", left + right }'
}

latest_snapshot_id() {
  repo="$1"

  latest_json="$(restic -r "$repo" snapshots latest --json 2>/dev/null || true)"
  if [ -z "$latest_json" ]; then
    latest_json="$(restic -r "$repo" snapshots --json 2>/dev/null || true)"
  fi

  printf '%s\n' "$latest_json" \
    | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | tail -n 1
}

ensure_backup_log_file() {
  mkdir -p "$BACKUP_LOG_DIR"

  if [ ! -f "$BACKUP_LOG_FILE" ]; then
    printf '%s\n' 'DATETIME,DATA_ADDED_MB,FOLDERS_ADDED,FILES_ADDED,DATA_REMOVED_MB,FILES_REMOVED,FOLDERS_REMOVED' > "$BACKUP_LOG_FILE"
  fi
}

append_backup_cycle_log() {
  ensure_backup_log_file

  run_datetime="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf '%s,%s,%s,%s,%s,%s,%s\n' \
    "$run_datetime" \
    "$CYCLE_DATA_ADDED_MB" \
    "$CYCLE_DIRS_ADDED" \
    "$CYCLE_FILES_ADDED" \
    "$CYCLE_DATA_REMOVED_MB" \
    "$CYCLE_FILES_REMOVED" \
    "$CYCLE_DIRS_REMOVED" \
    >> "$BACKUP_LOG_FILE"

  log "Backup delta logged to $BACKUP_LOG_FILE"
}

accumulate_cycle_metrics() {
  CYCLE_DATA_ADDED_MB="$(sum_mb "$CYCLE_DATA_ADDED_MB" "$LAST_DATA_ADDED_MB")"
  CYCLE_DATA_REMOVED_MB="$(sum_mb "$CYCLE_DATA_REMOVED_MB" "$LAST_DATA_REMOVED_MB")"
  CYCLE_DIRS_ADDED=$((CYCLE_DIRS_ADDED + LAST_DIRS_ADDED))
  CYCLE_DIRS_REMOVED=$((CYCLE_DIRS_REMOVED + LAST_DIRS_REMOVED))
  CYCLE_FILES_ADDED=$((CYCLE_FILES_ADDED + LAST_FILES_ADDED))
  CYCLE_FILES_REMOVED=$((CYCLE_FILES_REMOVED + LAST_FILES_REMOVED))
}

set_last_metrics_from_backup_output() {
  backup_output="$1"

  files_added_raw="$(printf '%s\n' "$backup_output" | sed -n 's/^Files:[[:space:]]*\([0-9,][0-9,]*\) new,.*$/\1/p' | tail -n 1)"
  dirs_added_raw="$(printf '%s\n' "$backup_output" | sed -n 's/^Dirs:[[:space:]]*\([0-9,][0-9,]*\) new,.*$/\1/p' | tail -n 1)"
  added_size_pair="$(printf '%s\n' "$backup_output" | sed -n 's/^[[:space:]]*Added to the repository:[[:space:]]*\([0-9.][0-9.]*\)[[:space:]]*\([A-Za-z][A-Za-z]*\).*/\1 \2/p' | tail -n 1)"

  LAST_FILES_ADDED="$(normalize_integer "$files_added_raw")"
  LAST_FILES_REMOVED="0"
  LAST_DIRS_ADDED="$(normalize_integer "$dirs_added_raw")"
  LAST_DIRS_REMOVED="0"
  LAST_DATA_ADDED_MB="$(size_pair_to_mb "$added_size_pair")"
  LAST_DATA_REMOVED_MB="0.000"
}

set_last_metrics_from_diff_output() {
  diff_output="$1"

  files_counts="$(printf '%s\n' "$diff_output" | sed -n 's/^Files:[[:space:]]*\([0-9,][0-9,]*\) new, [[:space:]]*\([0-9,][0-9,]*\) removed,.*$/\1 \2/p' | tail -n 1)"
  dirs_counts="$(printf '%s\n' "$diff_output" | sed -n 's/^Dirs:[[:space:]]*\([0-9,][0-9,]*\) new, [[:space:]]*\([0-9,][0-9,]*\) removed.*$/\1 \2/p' | tail -n 1)"
  added_size_pair="$(printf '%s\n' "$diff_output" | sed -n 's/^Added:[[:space:]]*\([0-9.][0-9.]*\)[[:space:]]*\([A-Za-z][A-Za-z]*\).*/\1 \2/p' | tail -n 1)"
  removed_size_pair="$(printf '%s\n' "$diff_output" | sed -n 's/^Removed:[[:space:]]*\([0-9.][0-9.]*\)[[:space:]]*\([A-Za-z][A-Za-z]*\).*/\1 \2/p' | tail -n 1)"

  set -- $files_counts
  files_added_raw="${1:-0}"
  files_removed_raw="${2:-0}"

  set -- $dirs_counts
  dirs_added_raw="${1:-0}"
  dirs_removed_raw="${2:-0}"

  LAST_FILES_ADDED="$(normalize_integer "$files_added_raw")"
  LAST_FILES_REMOVED="$(normalize_integer "$files_removed_raw")"
  LAST_DIRS_ADDED="$(normalize_integer "$dirs_added_raw")"
  LAST_DIRS_REMOVED="$(normalize_integer "$dirs_removed_raw")"
  LAST_DATA_ADDED_MB="$(size_pair_to_mb "$added_size_pair")"
  LAST_DATA_REMOVED_MB="$(size_pair_to_mb "$removed_size_pair")"
}

collect_backup_metrics() {
  repo="$1"
  previous_snapshot_id="$2"
  current_snapshot_id="$3"
  backup_output="$4"

  set_last_metrics_zero

  if [ -n "$previous_snapshot_id" ] && [ -n "$current_snapshot_id" ] && [ "$previous_snapshot_id" != "$current_snapshot_id" ]; then
    diff_output="$(restic -r "$repo" diff "$previous_snapshot_id" "$current_snapshot_id" 2>/dev/null || true)"

    if printf '%s\n' "$diff_output" | grep -q '^Files:'; then
      set_last_metrics_from_diff_output "$diff_output"
      return
    fi
  fi

  set_last_metrics_from_backup_output "$backup_output"
}

init_repo() {
  repo="$1"

  if restic -r "$repo" snapshots >/dev/null 2>&1; then
    return
  fi

  log "Initializing encrypted restic repository at $repo"
  restic -r "$repo" init
}

repo_has_snapshots() {
  repo="$1"

  snapshots_json="$(restic -r "$repo" snapshots --json 2>/dev/null || true)"
  compact_json="$(printf '%s' "$snapshots_json" | tr -d '[:space:]')"

  if [ "$compact_json" = "[]" ] || [ -z "$compact_json" ]; then
    return 1
  fi

  return 0
}

backup_source() {
  backup_name="$1"
  source_path="$2"
  repo_path="$3"

  set_last_metrics_zero

  if [ ! -d "$source_path" ]; then
    log "Skipping $backup_name backup because source path was not found: $source_path"
    return
  fi

  previous_snapshot_id="$(latest_snapshot_id "$repo_path")"
  backup_output_file="$(mktemp)"

  log "Starting incremental AES-encrypted backup for $backup_name"
  if restic -r "$repo_path" backup "$source_path" --host "$BACKUP_HOST_LABEL" --tag "$backup_name" > "$backup_output_file" 2>&1; then
    cat "$backup_output_file"
  else
    cat "$backup_output_file" >&2
    rm -f "$backup_output_file"
    log "ERROR: Backup command failed for $backup_name"
    exit 1
  fi

  backup_output="$(cat "$backup_output_file")"
  rm -f "$backup_output_file"

  current_snapshot_id="$(latest_snapshot_id "$repo_path")"
  collect_backup_metrics "$repo_path" "$previous_snapshot_id" "$current_snapshot_id" "$backup_output"

  log "Completed backup for $backup_name (added: ${LAST_DATA_ADDED_MB} MB, removed: ${LAST_DATA_REMOVED_MB} MB, files +${LAST_FILES_ADDED}/-${LAST_FILES_REMOVED}, folders +${LAST_DIRS_ADDED}/-${LAST_DIRS_REMOVED})."
}

verify_mysql_connection() {
  if mysql \
    --host "$MYSQL_HOST" \
    --port "$MYSQL_PORT" \
    --user "$MYSQL_USER" \
    --protocol=TCP \
    -e "SELECT 1" >/dev/null 2>&1; then
    return
  fi

  log "ERROR: Failed to connect to MySQL at ${MYSQL_HOST}:${MYSQL_PORT} as ${MYSQL_USER}."
  exit 1
}

dump_mysql_logical() {
  verify_mysql_connection

  rm -rf "$MYSQL_DUMP_STAGING"
  mkdir -p "$MYSQL_DUMP_STAGING"

  log "Creating MySQL globals dump (users/grants best-effort)"
  # Non-root users may lack PROCESS privilege for --all-databases globals;
  # always dump the portal database, and attempt globals when possible.
  if mysqldump \
    --host "$MYSQL_HOST" \
    --port "$MYSQL_PORT" \
    --user "$MYSQL_USER" \
    --protocol=TCP \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --databases "$MYSQL_DATABASE" \
    > "$MYSQL_DUMP_STAGING/${MYSQL_DATABASE}.sql" 2>/dev/null; then
    :
  else
    log "ERROR: mysqldump failed for database $MYSQL_DATABASE"
    exit 1
  fi

  {
    printf 'backup_generated_at_utc=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf 'mysql_host=%s\n' "$MYSQL_HOST"
    printf 'mysql_port=%s\n' "$MYSQL_PORT"
    printf 'mysql_user=%s\n' "$MYSQL_USER"
    printf 'mysql_database=%s\n' "$MYSQL_DATABASE"
  } > "$MYSQL_DUMP_STAGING/metadata.env"

  printf '%s\t%s\n' "$MYSQL_DATABASE" "${MYSQL_DATABASE}.sql" > "$MYSQL_DUMP_STAGING/database_map.tsv"

  rm -rf "$MYSQL_DUMP_CURRENT"
  mv "$MYSQL_DUMP_STAGING" "$MYSQL_DUMP_CURRENT"

  log "Logical MySQL dump completed for database: $MYSQL_DATABASE"
}

run_backup_cycle() {
  mkdir -p "$STORAGE_REPO" "$DOCUMENTS_REPO" "$ASSETS_REPO" "$TEMPLATES_REPO" "$MYSQL_REPO" "$MYSQL_DUMP_ROOT"

  init_repo "$STORAGE_REPO"
  init_repo "$DOCUMENTS_REPO"
  init_repo "$ASSETS_REPO"
  init_repo "$TEMPLATES_REPO"
  init_repo "$MYSQL_REPO"

  CYCLE_DATA_ADDED_MB="0.000"
  CYCLE_DATA_REMOVED_MB="0.000"
  CYCLE_DIRS_ADDED="0"
  CYCLE_DIRS_REMOVED="0"
  CYCLE_FILES_ADDED="0"
  CYCLE_FILES_REMOVED="0"

  backup_source "storage" "$STORAGE_SOURCE" "$STORAGE_REPO"
  accumulate_cycle_metrics

  backup_source "documents" "$DOCUMENTS_SOURCE" "$DOCUMENTS_REPO"
  accumulate_cycle_metrics

  backup_source "assets" "$ASSETS_SOURCE" "$ASSETS_REPO"
  accumulate_cycle_metrics

  backup_source "templates" "$TEMPLATES_SOURCE" "$TEMPLATES_REPO"
  accumulate_cycle_metrics

  dump_mysql_logical

  backup_source "mysql-logical" "$MYSQL_DUMP_CURRENT" "$MYSQL_REPO"
  accumulate_cycle_metrics

  append_backup_cycle_log
  log "Backup cycle totals (added: ${CYCLE_DATA_ADDED_MB} MB, removed: ${CYCLE_DATA_REMOVED_MB} MB, files +${CYCLE_FILES_ADDED}/-${CYCLE_FILES_REMOVED}, folders +${CYCLE_DIRS_ADDED}/-${CYCLE_DIRS_REMOVED})."
}

ensure_initial_backup_if_missing() {
  mkdir -p "$STORAGE_REPO" "$DOCUMENTS_REPO" "$ASSETS_REPO" "$TEMPLATES_REPO" "$MYSQL_REPO" "$MYSQL_DUMP_ROOT"

  init_repo "$STORAGE_REPO"
  init_repo "$DOCUMENTS_REPO"
  init_repo "$ASSETS_REPO"
  init_repo "$TEMPLATES_REPO"
  init_repo "$MYSQL_REPO"

  missing_initial_backup="0"

  if ! repo_has_snapshots "$STORAGE_REPO"; then
    missing_initial_backup="1"
    log "No existing storage backup snapshot found."
  fi

  if ! repo_has_snapshots "$MYSQL_REPO"; then
    missing_initial_backup="1"
    log "No existing MySQL logical backup snapshot found."
  fi

  if [ "$missing_initial_backup" = "1" ]; then
    log "No complete existing backup detected. Running one-time initial backup now."
    run_backup_cycle
    now_epoch="$(date +%s)"
    printf '%s' "$now_epoch" > "$LAST_RUN_FILE"
    log "Initial backup completed."
    return
  fi

  log "Existing backup snapshots detected. Continuing with scheduled backup loop."
}

LAST_RUN_FILE="${BACKUP_ROOT%/}/.last_backup_epoch"

log "Backup service started. Schedule: $BACKUP_START_TIME every $BACKUP_INTERVAL_DAYS day(s)."

ensure_backup_log_file

ensure_initial_backup_if_missing

while true; do
  wait_seconds="$(seconds_until_start_time)"
  log "Waiting $wait_seconds seconds until next backup window at $BACKUP_START_TIME."
  sleep "$wait_seconds"

  now_epoch="$(date +%s)"
  should_run="1"

  if [ -f "$LAST_RUN_FILE" ]; then
    last_epoch="$(cat "$LAST_RUN_FILE" 2>/dev/null || true)"
    case "$last_epoch" in
      ''|*[!0-9]*)
        last_epoch="0"
        ;;
    esac

    if [ "$last_epoch" -gt 0 ]; then
      elapsed_days=$(((now_epoch - last_epoch) / 86400))
      if [ "$elapsed_days" -lt "$BACKUP_INTERVAL_DAYS" ]; then
        should_run="0"
        log "Skipping backup window. Only $elapsed_days day(s) elapsed; required: $BACKUP_INTERVAL_DAYS day(s)."
      fi
    fi
  fi

  if [ "$should_run" = "1" ]; then
    run_backup_cycle
    printf '%s' "$now_epoch" > "$LAST_RUN_FILE"
    log "Backup cycle finished at scheduled window."
  fi
done
