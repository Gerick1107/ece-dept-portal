#!/bin/sh
set -e

echo "Waiting for MySQL..."
until python -c "
import os, time
import pymysql
host = os.environ.get('MYSQL_HOST', 'mysql')
port = int(os.environ.get('MYSQL_PORT', '3306'))
user = os.environ.get('MYSQL_USER', 'portal_user')
password = os.environ.get('MYSQL_PASSWORD', 'portal_pass')
db = os.environ.get('MYSQL_DATABASE', 'ece_dept_portal')
for _ in range(60):
    try:
        pymysql.connect(host=host, port=port, user=user, password=password, database=db, connect_timeout=3)
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit('MySQL not reachable')
" 2>/dev/null; do
  sleep 2
done

echo "Running migrations..."
# Use "heads" so a temporary multi-head graph cannot brick container startup
# (that previously manifested as nginx 502 → UI "Login failed").
if ! alembic upgrade heads; then
  echo "ERROR: alembic upgrade heads failed. Backend will not start."
  alembic heads || true
  alembic history -r -3: || true
  exit 1
fi

exec "$@"
