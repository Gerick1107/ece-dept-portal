FROM restic/restic:0.18.1 AS restic-binary

FROM mysql:8.0

# Client tools (mysqldump/mysql) come from the mysql image.
COPY --from=restic-binary /usr/bin/restic /usr/local/bin/restic

COPY ./restic_backup_loop.sh /opt/backup/restic_backup_loop.sh
RUN chmod 0755 /opt/backup/restic_backup_loop.sh

ENTRYPOINT ["/bin/sh", "/opt/backup/restic_backup_loop.sh"]
