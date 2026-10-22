#!/usr/bin/env python3
"""ЛР3: налаштування Zabbix через API (вузли, шаблони, елементи, веб-сценарій, тригери, користувач для Grafana)."""
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

URL = "http://localhost:8081/api_jsonrpc.php"
LAB1_SERVICES = {"db": "db", "proxy": "proxy", "app": "lab1-app-1"}
SNMP_COMMUNITY = "lab3comm"


def load_env():
    env = {}
    for line in Path(".env").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env


class Zabbix:
    def __init__(self):
        self.token = None
        self.n = 0

    def call(self, method, params=None, auth=True):
        self.n += 1
        headers = {"Content-Type": "application/json-rpc"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        r = requests.post(URL, headers=headers, timeout=30,
                          json={"jsonrpc": "2.0", "method": method, "params": params if params is not None else [], "id": self.n})
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"{method}: {data['error'].get('data') or data['error']}")
        return data["result"]

    def wait_ready(self):
        # чекаємо, поки сервер створить схему БД і API стане доступним
        for _ in range(60):
            try:
                self.call("apiinfo.version", auth=False)
                return
            except Exception:
                time.sleep(5)
        sys.exit("Zabbix API недоступний")

    def login(self, env):
        # спочатку пробуємо вже змінений пароль, потім типовий
        for pw in (env["ZBX_ADMIN_PASSWORD"], "zabbix"):
            try:
                self.token = self.call("user.login", {"username": "Admin", "password": pw}, auth=False)
                return pw
            except RuntimeError:
                continue
        sys.exit("Не вдалося увійти як Admin")


def one(rows, key, value):
    for r in rows:
        if r.get(key) == value:
            return r
    return None


def main():
    env = load_env()
    z = Zabbix()
    z.wait_ready()
    used_pw = z.login(env)
    print("Версія API:", z.call("apiinfo.version", auth=False))

    # 1. зміна типового пароля адміністратора
    if used_pw == "zabbix":
        admin = z.call("user.get", {"filter": {"username": "Admin"}})[0]
        z.call("user.update", {"userid": admin["userid"], "current_passwd": "zabbix", "passwd": env["ZBX_ADMIN_PASSWORD"]})
        z.login(env)
        print("Пароль Admin змінено")

    # 2. група вузлів
    grp = z.call("hostgroup.get", {"filter": {"name": "Lab3"}})
    group_id = grp[0]["groupid"] if grp else z.call("hostgroup.create", {"name": "Lab3"})["groupids"][0]

    def template_id(name):
        t = z.call("template.get", {"filter": {"host": [name]}})
        if not t:
            sys.exit(f"Шаблон не знайдено: {name}")
        return t[0]["templateid"]

    # 3. вузол з агентом: шаблони Linux та Docker
    if not z.call("host.get", {"filter": {"host": ["lab1-host"]}}):
        z.call("host.create", {
            "host": "lab1-host", "name": "lab1-host (Docker-хост ЛР1)",
            "interfaces": [{"type": 1, "main": 1, "useip": 0, "ip": "", "dns": "zabbix-agent", "port": "10050"}],
            "groups": [{"groupid": group_id}],
            "templates": [{"templateid": template_id("Linux by Zabbix agent")},
                          {"templateid": template_id("Docker by Zabbix agent 2")}],
        })
        print("Вузол lab1-host створено")
    host_id = z.call("host.get", {"filter": {"host": ["lab1-host"]}})[0]["hostid"]
    iface_id = z.call("hostinterface.get", {"hostids": host_id})[0]["interfaceid"]

    # 4. елементи для станів контейнерів ЛР1 (плагін Docker): головний JSON + залежні
    items = {i["key_"]: i for i in z.call("item.get", {"hostids": host_id, "output": ["itemid", "key_"]})}
    for svc, cname in LAB1_SERVICES.items():
        mkey = f"docker.container_info[{cname},full]"
        if mkey not in items:
            z.call("item.create", {"hostid": host_id, "name": f"Docker: {svc} ({cname}) inspect JSON", "key_": mkey,
                                   "type": 0, "value_type": 4, "delay": "10s", "interfaceid": iface_id,
                                   "history": "1d", "tags": [{"tag": "lab", "value": "lab1"}]})
            items[mkey] = z.call("item.get", {"hostids": host_id, "filter": {"key_": mkey}, "output": ["itemid"]})[0]
        master = items[mkey]["itemid"]
        dependents = [
            (f"lab1.{svc}.state", f"LR1 {svc}: стан контейнера", 4, "$.State.Status", False),
            (f"lab1.{svc}.up", f"LR1 {svc}: контейнер запущено (1/0)", 3, "$.State.Running", True),
        ]
        for key, name, vtype, path, to_dec in dependents:
            if key in items:
                continue
            pre = [{"type": 12, "params": path, "error_handler": 0, "error_handler_params": ""}]
            if to_dec:
                pre.append({"type": 6, "params": "", "error_handler": 0, "error_handler_params": ""})
            z.call("item.create", {"hostid": host_id, "name": name, "key_": key, "type": 18, "master_itemid": master,
                                   "value_type": vtype, "history": "7d", "preprocessing": pre,
                                   "tags": [{"tag": "lab", "value": "lab1"}]})
    print("Елементи станів контейнерів готові")

    # 5. веб-сценарій (безагентна перевірка) через проксі ЛР1
    if not z.call("httptest.get", {"hostids": host_id, "filter": {"name": "lab1-app"}}):
        z.call("httptest.create", {
            "name": "lab1-app", "hostid": host_id, "delay": "10s", "retries": 1,
            "steps": [{"name": "proxy", "url": "http://proxy:80/", "status_codes": "200", "timeout": "5s", "no": 1}],
        })
        print("Веб-сценарій lab1-app створено")

    # 6. SNMP-вузол
    if not z.call("host.get", {"filter": {"host": ["net-device"]}}):
        z.call("host.create", {
            "host": "net-device", "name": "net-device (SNMP-пристрій)",
            "interfaces": [{"type": 2, "main": 1, "useip": 0, "ip": "", "dns": "net-device", "port": "161",
                            "details": {"version": 2, "bulk": 1, "community": "{$SNMP_COMMUNITY}"}}],
            "groups": [{"groupid": group_id}],
            "templates": [{"templateid": template_id("Network Generic Device by SNMP")}],
            "macros": [{"macro": "{$SNMP_COMMUNITY}", "value": SNMP_COMMUNITY},
                       {"macro": "{$SNMP_IN_BPS_MAX}", "value": "10000000"}],
        })
        print("Вузол net-device створено")
    snmp_host = z.call("host.get", {"filter": {"host": ["net-device"]}})[0]["hostid"]
    snmp_iface = z.call("hostinterface.get", {"hostids": snmp_host})[0]["interfaceid"]

    # індекс eth0 в ifTable беремо з самого пристрою
    walk = subprocess.run(["docker", "compose", "exec", "-T", "net-device", "snmpwalk", "-v2c", "-c", SNMP_COMMUNITY,
                           "-On", "127.0.0.1", "1.3.6.1.2.1.2.2.1.2"], capture_output=True, text=True).stdout
    idx = next(l.split(" = ")[0].rsplit(".", 1)[1] for l in walk.splitlines() if l.endswith("STRING: eth0"))
    snmp_items = {i["key_"] for i in z.call("item.get", {"hostids": snmp_host, "output": ["key_"]})}
    specs = [
        ("snmp.uptime", "SNMP: sysUpTime (с)", "1.3.6.1.2.1.1.3.0", 0, "s",
         [{"type": 1, "params": "0.01", "error_handler": 0, "error_handler_params": ""}]),
        ("snmp.ifoper.eth0", "SNMP: ifOperStatus eth0 (1=up)", f"1.3.6.1.2.1.2.2.1.8.{idx}", 3, "", []),
        ("snmp.ifin.eth0", "SNMP: вхідний трафік eth0 (біт/с)", f"1.3.6.1.2.1.31.1.1.1.6.{idx}", 0, "bps",
         [{"type": 10, "params": "", "error_handler": 0, "error_handler_params": ""},
          {"type": 1, "params": "8", "error_handler": 0, "error_handler_params": ""}]),
        ("snmp.ifout.eth0", "SNMP: вихідний трафік eth0 (біт/с)", f"1.3.6.1.2.1.31.1.1.1.10.{idx}", 0, "bps",
         [{"type": 10, "params": "", "error_handler": 0, "error_handler_params": ""},
          {"type": 1, "params": "8", "error_handler": 0, "error_handler_params": ""}]),
    ]
    for key, name, oid, vtype, units, pre in specs:
        if key not in snmp_items:
            z.call("item.create", {"hostid": snmp_host, "name": name, "key_": key, "type": 20, "snmp_oid": oid,
                                   "value_type": vtype, "units": units, "delay": "10s", "interfaceid": snmp_iface,
                                   "history": "7d", "preprocessing": pre})
    print("SNMP-елементи готові (індекс eth0 =", idx + ")")

    # 7. тригери
    triggers = [
        ("LR1: застосунок недоступний через проксі (HTTP != 200)",
         "last(/lab1-host/web.test.rspcode[lab1-app,proxy])<>200 or last(/lab1-host/web.test.fail[lab1-app])>0", 4),
        ("LR1: контейнер БД зупинено або відсутній",
         "last(/lab1-host/lab1.db.up)=0 or nodata(/lab1-host/lab1.db.up,60s)=1", 4),
        ("SNMP: пристрій net-device недоступний",
         "nodata(/net-device/snmp.uptime,60s)=1", 3),
        ("SNMP: вхідний трафік eth0 перевищує поріг",
         "avg(/net-device/snmp.ifin.eth0,1m)>{$SNMP_IN_BPS_MAX}", 2),
    ]
    existing = {t["description"] for t in z.call("trigger.get", {"output": ["description"]})}
    for desc, expr, prio in triggers:
        if desc not in existing:
            z.call("trigger.create", {"description": desc, "expression": expr, "priority": prio})
    print("Тригерів налаштовано:", len(triggers))

    # 8. користувач лише для читання (для Grafana)
    ug = z.call("usergroup.get", {"filter": {"name": "grafana-readonly"}})
    ug_id = ug[0]["usrgrpid"] if ug else z.call("usergroup.create", {
        "name": "grafana-readonly", "hostgroup_rights": [{"id": group_id, "permission": 2}]})["usrgrpids"][0]
    if not z.call("user.get", {"filter": {"username": "grafana"}}):
        role = one(z.call("role.get", {"output": ["roleid", "name"]}), "name", "User role")
        z.call("user.create", {"username": "grafana", "passwd": env["GRAFANA_ZBX_PASSWORD"],
                               "roleid": role["roleid"], "usrgrps": [{"usrgrpid": ug_id}]})
        print("Користувача grafana (read-only) створено")

    # вимикаємо типовий вузол «Zabbix server» (в нього немає агента, він лише створює шум)
    zs = z.call("host.get", {"filter": {"host": ["Zabbix server"]}, "output": ["hostid", "status"]})
    if zs and zs[0]["status"] == "0":
        z.call("host.update", {"hostid": zs[0]["hostid"], "status": 1})

    # 9. швидке виявлення: виконати правила виявлення негайно
    for hid in (host_id, snmp_host):
        rules = z.call("discoveryrule.get", {"hostids": hid, "output": ["itemid", "name"]})
        tasks = [{"type": 6, "request": {"itemid": r["itemid"]}} for r in rules]
        if tasks:
            z.call("task.create", tasks)
    print("Налаштування Zabbix завершено")


if __name__ == "__main__":
    main()
