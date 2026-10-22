#!/usr/bin/env python3
"""Генерує дашборд Grafana (grafana/dashboards/lab3.json); часовий діапазон бере з evidence/fault.json."""
import json
from datetime import datetime, timezone
from pathlib import Path

DS = {"type": "alexanderzobnin-zabbix-datasource", "uid": "zabbix"}


def target(ref, host, item):
    # запит до Zabbix datasource: група, вузол, елемент
    return {"refId": ref, "datasource": DS, "queryType": "0", "group": {"filter": "Lab3"}, "host": {"filter": host},
            "application": {"filter": ""}, "itemTag": {"filter": ""}, "item": {"filter": item},
            "functions": [], "options": {"showDisableItems": False}}


def mapping(pairs):
    return [{"type": "value", "options": {str(k): {"text": t, "color": c, "index": i} for i, (k, t, c) in enumerate(pairs)}}]


def panel(pid, title, ptype, x, y, targets, unit="short", mappings=None, thresholds=None, desc=""):
    defaults = {"unit": unit, "custom": {}, "mappings": mappings or [],
                "color": {"mode": "thresholds" if ptype == "state-timeline" else "palette-classic"},
                "thresholds": thresholds or {"mode": "absolute", "steps": [{"color": "green", "value": None}]}}
    return {"id": pid, "title": title, "type": ptype, "datasource": DS, "description": desc,
            "gridPos": {"x": x, "y": y, "w": 12, "h": 8}, "targets": targets,
            "fieldConfig": {"defaults": defaults, "overrides": []},
            "options": {"showValue": "auto", "legend": {"displayMode": "list", "placement": "bottom"}} if ptype == "state-timeline"
            else {"legend": {"displayMode": "list", "placement": "bottom"}}}


def main():
    fault = json.loads(Path("evidence/fault.json").read_text()) if Path("evidence/fault.json").exists() else None
    if fault:
        iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # діапазон: 2 хвилини до збою і 2 хвилини після відновлення
        time_range = {"from": iso(fault["stop"] - 120), "to": iso(fault["start"] + 120)}
    else:
        time_range = {"from": "now-1h", "to": "now"}
    red_green = {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 200}, {"color": "red", "value": 300}]}
    panels = [
        panel(1, "Доступність застосунку (HTTP-код через проксі)", "state-timeline", 0, 0,
              [target("A", "/lab1-host/", "/Response code for step/")],
              mappings=mapping([(200, "200 OK", "green"), (503, "503 збій", "red"), (0, "немає відповіді", "red")]),
              thresholds=red_green, desc="Код відповіді веб-сценарію Zabbix; 200 - норма"),
        panel(2, "Час відповіді застосунку, с", "timeseries", 12, 0,
              [target("A", "/lab1-host/", "/Response time for step/")], unit="s"),
        panel(3, "Стан контейнерів проєкту ЛР1", "state-timeline", 0, 8,
              [target("A", "/lab1-host/", "/LR1 .*контейнер запущено/")],
              mappings=mapping([(1, "running", "green"), (0, "stopped", "red")]),
              thresholds={"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]},
              desc="1 - контейнер запущено, 0 - зупинено (плагін Docker, агент 2)"),
        panel(4, "Трафік eth0 SNMP-пристрою, біт/с", "timeseries", 12, 8,
              [target("A", "/net-device/", "/SNMP: (вхідний|вихідний) трафік/")], unit="bps"),
    ]
    dash = {"uid": "lab3-monitoring", "title": "ЛР3: Моніторинг інфраструктури", "schemaVersion": 39, "version": 1,
            "refresh": "10s", "time": time_range, "timezone": "browser", "panels": panels, "tags": ["lab3"]}
    Path("grafana/dashboards/lab3.json").write_text(json.dumps(dash, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Дашборд записано, діапазон:", time_range)


if __name__ == "__main__":
    main()
