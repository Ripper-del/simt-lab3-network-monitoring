#!/usr/bin/env python3
"""ЛР3 (високий рівень): власний шаблон з макросом та шаблон low-level discovery контейнерів."""
import sys

from configure_zabbix import Zabbix, load_env

HTTP_TPL = "Lab3 HTTP template"
LLD_TPL = "Lab3 container discovery"


def tpl_id(z, name, group_id):
    t = z.call("template.get", {"filter": {"host": [name]}})
    if t:
        return t[0]["templateid"], False
    return z.call("template.create", {"host": name, "groups": [{"groupid": group_id}]})["templateids"][0], True


def setup(z):
    # у Zabbix 7 шаблони лежать у групах шаблонів
    tg = z.call("templategroup.get", {"filter": {"name": "Templates"}})[0]["groupid"]
    group_id = tg
    host_id = z.call("host.get", {"filter": {"host": ["lab1-host"]}})[0]["hostid"]

    # --- шаблон 1: елемент даних + обчислюваний елемент + макрос + тригер
    tid, new = tpl_id(z, HTTP_TPL, group_id)
    if new:
        z.call("usermacro.create", {"hostid": tid, "macro": "{$LAB3.RT.MAX.MS}", "value": "500",
                                    "description": "Поріг часу відповіді проксі, мс"})
        z.call("item.create", {"hostid": tid, "name": "Lab3: час відповіді HTTP проксі, с", "key_": "net.tcp.service.perf[http,proxy,80]",
                               "type": 3, "value_type": 0, "delay": "10s", "units": "s", "history": "7d"})
        z.call("item.create", {"hostid": tid, "name": "Lab3: час відповіді HTTP проксі, мс", "key_": "lab3.rt.ms",
                               "type": 15, "value_type": 0, "delay": "10s", "units": "ms", "history": "7d",
                               "params": "last(//net.tcp.service.perf[http,proxy,80])*1000"})
        z.call("trigger.create", {"description": "Lab3: час відповіді проксі перевищує {$LAB3.RT.MAX.MS} мс",
                                  "expression": f"avg(/{HTTP_TPL}/lab3.rt.ms,1m)>{{$LAB3.RT.MAX.MS}}", "priority": 2})
        print("Шаблон", HTTP_TPL, "створено")

    # --- шаблон 2: LLD контейнерів
    lid, new = tpl_id(z, LLD_TPL, group_id)
    if new:
        rule = z.call("discoveryrule.create", {
            "hostid": lid, "name": "Виявлення контейнерів ЛР1", "key_": "docker.containers.discovery[true]",
            "type": 0, "delay": "30s", "lifetime": "1h",
            "filter": {"evaltype": 0, "conditions": [{"macro": "{#NAME}", "value": r"^/(db|proxy|lab1-app-\d+)$", "operator": 8}]},
        })["itemids"][0]
        master = z.call("itemprototype.create", {
            "hostid": lid, "ruleid": rule, "name": "Inspect {#NAME}", "key_": "lab3.container.info[{#NAME}]",
            "type": 0, "value_type": 4, "delay": "30s", "history": "1d"})
        # ключ агента з параметрами {#NAME},full
        z.call("itemprototype.update", {"itemid": master["itemids"][0], "key_": "docker.container_info[{#NAME},full]"})
        z.call("itemprototype.create", {
            "hostid": lid, "ruleid": rule, "name": "Контейнер {#NAME} запущено (1/0)", "key_": "lab3.container.up[{#NAME}]",
            "type": 18, "master_itemid": master["itemids"][0], "value_type": 3, "history": "7d",
            "preprocessing": [{"type": 12, "params": "$.State.Running", "error_handler": 0, "error_handler_params": ""},
                              {"type": 6, "params": "", "error_handler": 0, "error_handler_params": ""}]})
        z.call("triggerprototype.create", {
            "description": "Lab3: контейнер {#NAME} зупинено",
            "expression": f"last(/{LLD_TPL}/lab3.container.up[{{#NAME}}])=0", "priority": 3})
        print("Шаблон", LLD_TPL, "створено")

    # прив'язка до вузла
    linked = {t["templateid"] for t in z.call("host.get", {"hostids": host_id, "selectParentTemplates": ["templateid"]})[0]["parentTemplates"]}
    add = [t for t in (tid, lid) if t not in linked]
    if add:
        z.call("host.update", {"hostid": host_id, "templates": [{"templateid": t} for t in list(linked) + add]})
        print("Шаблони прив'язано до lab1-host")
    for r in z.call("discoveryrule.get", {"hostids": host_id, "search": {"key_": "docker.containers.discovery[true]"}, "output": ["itemid"]}):
        z.call("task.create", [{"type": 6, "request": {"itemid": r["itemid"]}}])


def macro(z, value):
    host_id = z.call("host.get", {"filter": {"host": ["lab1-host"]}})[0]["hostid"]
    cur = z.call("usermacro.get", {"hostids": host_id, "filter": {"macro": "{$LAB3.RT.MAX.MS}"}})
    if value is None:
        for m in cur:
            z.call("usermacro.delete", [m["hostmacroid"]])
        print("Макрос на рівні вузла видалено (діє значення шаблону 500)")
    elif cur:
        z.call("usermacro.update", {"hostmacroid": cur[0]["hostmacroid"], "value": value})
    else:
        z.call("usermacro.create", {"hostid": host_id, "macro": "{$LAB3.RT.MAX.MS}", "value": value})
        print("Макрос на рівні вузла перевизначено:", value)


if __name__ == "__main__":
    zbx = Zabbix()
    zbx.login(load_env())
    cmd = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if cmd == "setup":
        setup(zbx)
    elif cmd == "macro":
        macro(zbx, sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "reset" else None)
