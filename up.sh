#!/usr/bin/env bash
# Розгортання системи моніторингу однією командою (потрібен запущений проєкт ЛР1)
set -euo pipefail
cd "$(dirname "$0")"
# паролі генеруються локально і не потрапляють у git
if [[ ! -f .env ]]; then
  {
    echo "ZBX_DB_PASSWORD=$(openssl rand -hex 12)"
    echo "ZBX_ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '/+=')Aa1"
    echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '/+=')Aa1"
    echo "GRAFANA_ZBX_PASSWORD=$(openssl rand -base64 12 | tr -d '/+=')Aa1"
  } > .env
  chmod 600 .env
fi
docker network inspect lab1-frontend >/dev/null 2>&1 || { echo "Спочатку запустіть проєкт ЛР1 (docker compose up -d у LR1)"; exit 1; }
docker compose up -d --build
[[ -x .venv/bin/python ]] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
# налаштування Zabbix через API
.venv/bin/python configure_zabbix.py
