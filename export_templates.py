#!/usr/bin/env python3
"""Експорт власних шаблонів Zabbix у YAML (додаток до звіту)."""
from configure_zabbix import Zabbix, load_env

z = Zabbix()
z.login(load_env())
for name, fname in (("Lab3 HTTP template", "lab3_http_template"), ("Lab3 container discovery", "lab3_container_discovery")):
    t = z.call("template.get", {"filter": {"host": [name]}})[0]["templateid"]
    open(f"export/{fname}.yaml", "w", encoding="utf-8").write(z.call("configuration.export", {"format": "yaml", "options": {"templates": [t]}}))
    print("exported", name)
