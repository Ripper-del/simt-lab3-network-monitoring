#!/usr/bin/env python3
"""ЛР3: керований збій БД проєкту ЛР1 та вимірювання часу появи й закриття проблем у Zabbix."""
import json
import subprocess
import time
from datetime import datetime

from configure_zabbix import Zabbix, load_env

LAB1 = ["docker", "compose", "-f", "../LR1/docker-compose.yml", "-p", "lab1"]
WATCH = ["LR1: застосунок недоступний через проксі (HTTP != 200)", "LR1: контейнер БД зупинено або відсутній"]
HOLD_SECONDS = 25


def fmt(t):
    return datetime.fromtimestamp(t).strftime("%H:%M:%S") if t else "-"


def problems(z):
    """Проблеми за нашими тригерами (з часом події та закриття)."""
    res = {}
    for p in z.call("problem.get", {"recent": True, "output": "extend", "sortfield": ["eventid"], "sortorder": "DESC"}):
        if p["name"] in WATCH and p["name"] not in res:
            res[p["name"]] = p
    return res


def main():
    z = Zabbix()
    z.login(load_env())
    t_stop = time.time()
    subprocess.run(LAB1 + ["stop", "db"], check=True, capture_output=True)
    print(f"{fmt(t_stop)} зупинено db")

    found = {}
    while len(found) < len(WATCH) and time.time() - t_stop < 240:
        for name, p in problems(z).items():
            if name not in found and int(p["clock"]) >= int(t_stop) - 1 and p["r_eventid"] == "0":
                found[name] = int(p["clock"])
                print(f"{fmt(time.time())} з'явилась проблема: {name} (час події {fmt(int(p['clock']))})")
        time.sleep(2)

    time.sleep(HOLD_SECONDS)
    t_start = time.time()
    subprocess.run(LAB1 + ["start", "db"], check=True, capture_output=True)
    print(f"{fmt(t_start)} запущено db")

    closed = {}
    while len(closed) < len(WATCH) and time.time() - t_start < 240:
        for name in WATCH:
            p = problems(z).get(name)
            if p and name not in closed and p["r_eventid"] != "0":
                ev = z.call("event.get", {"eventids": p["r_eventid"], "output": ["clock"]})[0]
                closed[name] = int(ev["clock"])
                print(f"{fmt(time.time())} проблему закрито: {name} (час закриття {fmt(closed[name])})")
        time.sleep(2)

    result = {"stop": t_stop, "start": t_start, "problems": [
        {"name": n, "opened": found.get(n), "closed": closed.get(n),
         "detect_delay_s": round(found[n] - t_stop, 1) if n in found else None,
         "recovery_delay_s": round(closed[n] - t_start, 1) if n in closed else None} for n in WATCH]}
    json.dump(result, open("evidence/fault.json", "w"), indent=2)
    print("\nпроблема | з'явилась | закрита | затримка виявлення, с | затримка закриття, с")
    for p in result["problems"]:
        print(f"{p['name']} | {fmt(p['opened'])} | {fmt(p['closed'])} | {p['detect_delay_s']} | {p['recovery_delay_s']}")
    print(f"зупинка db: {fmt(t_stop)}, старт db: {fmt(t_start)}")


if __name__ == "__main__":
    main()
