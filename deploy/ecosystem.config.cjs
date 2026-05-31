const path = require("path");
const root = path.join(__dirname, "..");

module.exports = {
  apps: [
    {
      name: "ece-dept-portal-api",
      cwd: path.join(root, "backend"),
      script: path.join(root, "backend", ".venv", "Scripts", "python.exe"),
      args: "-m gunicorn app.main:app -c ../deploy/gunicorn.conf.py",
      interpreter: "none",
      env: {
        PYTHONPATH: path.join(root, "backend"),
      },
      instances: 1,
      autorestart: true,
      max_memory_restart: "1G",
    },
    {
      name: "ece-dept-portal-web",
      cwd: path.join(root, "frontend"),
      script: "npm",
      args: "run preview -- --host 0.0.0.0 --port 5173",
      interpreter: "none",
      autorestart: true,
    },
  ],
};
