# ЛР3. Моніторинг мережевої інфраструктури

Zabbix 7.0 (server, web, PostgreSQL, agent2), SNMP-пристрій та Grafana. Налаштування виконується через JSON-RPC API Zabbix.

## Запуск (потрібна запущена ЛР1: `docker compose up -d` у репозиторії ЛР1)
    ./up.sh                               # паролі генеруються в .env, система розгортається і налаштовується
    # Zabbix: http://localhost:8081 (Admin, пароль у .env), Grafana: http://localhost:3000
    .venv/bin/python fault_experiment.py  # експеримент зі збоєм БД
    .venv/bin/python configure_template.py setup   # власні шаблони, макрос, low-level discovery

## Склад
- `docker-compose.yml`, `snmpd/`, `grafana/` (provisioning і дашборд), `export/` (шаблони Zabbix у YAML).
- `configure_zabbix.py`, `configure_template.py`, `fault_experiment.py`, `zbx_query.py`.
- `evidence/`, `report/` (PDF, DOCX).
- Файл `.env` з паролями не зберігається в git.
- Перегенерація звіту: `pip install -r common/requirements-report.txt && LAB_AUTHOR="Прізвище_Ім'я" LAB_GROUP="ІО-XX" python build_report.py`
