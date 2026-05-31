-- Run once in MySQL Workbench as root on Local MySQL (port 3306).
-- Creates the same app user/database as the old Docker compose file.

CREATE DATABASE IF NOT EXISTS ece_dept_portal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'portal_user'@'localhost' IDENTIFIED BY 'portal_pass';
CREATE USER IF NOT EXISTS 'portal_user'@'127.0.0.1' IDENTIFIED BY 'portal_pass';

GRANT ALL PRIVILEGES ON ece_dept_portal.* TO 'portal_user'@'localhost';
GRANT ALL PRIVILEGES ON ece_dept_portal.* TO 'portal_user'@'127.0.0.1';

FLUSH PRIVILEGES;
