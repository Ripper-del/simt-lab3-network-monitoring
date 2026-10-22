#!/usr/bin/env python3
"""Допоміжні запити до Zabbix API для звіту (стан вузлів, останні дані, проблеми)."""
import sys
import time
from datetime import datetime

from configure_zabbix import Zabbix, load_env


def ts(v):
    return datetime.fromtimestamp(int(v)).strftime("%H:%M:%S") if int(v) else "-"


def main(cmd):
    env = load_env()
    z = Zabbix()
    z.login(env)
    if cmd == "hosts":
        for h in z.call("host.get", {"output": ["host", "available", "snmp_available", "status"], "selectInterfaces": ["type", "available", "dns", "port"]}):
            print(h["host"], [(i["type"], i["dns"], i["port"], i["available"]) for i in h["interfaces"]])
    elif cmd == "latest":
        pats = sys.argv[2:]
        for it in z.call("item.get", {"output": ["name", "key_", "delay", "lastvalue", "units", "state", "error", "lastclock"],
                                      "selectHosts": ["host"], "sortfield": "name", "webitems": True, "monitored": True, "filter": {"flags": [0, 4]}}):
            if it["hosts"][0]["host"] == "Zabbix server":
                continue
            line = f"{it['hosts'][0]['host']:<10} {it['key_']:<55} delay={it['delay']:<4} last={it['lastvalue'][:40]!r} {it['units']} state={it['state']}"
            if not pats or any(p in it["key_"] or p in it["name"] for p in pats):
                print(line)
    elif cmd == "problems":
        for p in z.call("problem.get", {"recent": True, "sortfield": ["eventid"], "sortorder": "DESC", "output": "extend"}):
            print(ts(p["clock"]), p["name"], "severity", p["severity"], "resolved" if p["r_eventid"] != "0" else "ACTIVE")
    elif cmd == "triggers":
        for t in z.call("trigger.get", {"output": ["description", "expression", "priority", "value", "error"], "expandExpression": True, "selectHosts": ["host"], "filter": {"flags": [0, 4]}, "monitored": True, "search": {"description": ["LR1:", "SNMP:", "Lab3:"]}, "searchByAny": True}):
            print(t["hosts"][0]["host"], "|", t["description"], "|", t["expression"], "| prio", t["priority"], "| value", t["value"], t["error"])


if __name__ == "__main__":
    main(sys.argv[1])
