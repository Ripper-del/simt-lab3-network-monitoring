#!/usr/bin/env python3
"""Знімки веб-інтерфейсів Zabbix та Grafana для звіту (потрібен playwright)."""
import sys
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from configure_zabbix import Zabbix, load_env

ZBX = "http://localhost:8081"
GRAF = "http://localhost:3000"
OUT = "evidence/shots/"


def main():
    env = load_env()
    z = Zabbix()
    z.login(env)
    hid = {h["host"]: h["hostid"] for h in z.call("host.get", {"output": ["host"]})}
    pages = [
        ("zbx-sysinfo", f"{ZBX}/zabbix.php?action=report.status"),
        ("zbx-hosts", f"{ZBX}/zabbix.php?action=host.view&filter_set=1&filter_groupids[]=" + z.call("hostgroup.get", {"filter": {"name": "Lab3"}})[0]["groupid"]),
        ("zbx-latest-linux", f"{ZBX}/zabbix.php?action=latest.view&filter_set=1&filter_hostids[]={hid['lab1-host']}&filter_name=" + quote("system.cpu.util")),
        ("zbx-latest-docker", f"{ZBX}/zabbix.php?action=latest.view&filter_set=1&filter_hostids[]={hid['lab1-host']}&filter_name=" + quote("LR1")),
        ("zbx-latest-web", f"{ZBX}/zabbix.php?action=latest.view&filter_set=1&filter_hostids[]={hid['lab1-host']}&filter_name=" + quote("lab1-app")),
        ("zbx-latest-snmp", f"{ZBX}/zabbix.php?action=latest.view&filter_set=1&filter_hostids[]={hid['net-device']}&filter_name=" + quote("SNMP")),
        ("zbx-latest-lld", f"{ZBX}/zabbix.php?action=latest.view&filter_set=1&filter_hostids[]={hid['lab1-host']}&filter_name=" + quote("lab3.container.up")),
        ("zbx-web", f"{ZBX}/zabbix.php?action=web.view&filter_set=1&filter_hostids[]={hid['lab1-host']}"),
        ("zbx-problems", f"{ZBX}/zabbix.php?action=problem.view&filter_set=1&filter_show=2&show_timeline=0&from=now-1h&to=now&filter_name=&filter_severities[]=0&filter_severities[]=1&filter_severities[]=2&filter_severities[]=3&filter_severities[]=4&filter_severities[]=5"),
        ("grafana-dashboard", f"{GRAF}/d/lab3-monitoring/?kiosk"),
    ]
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1500, "height": 900}, device_scale_factor=1)
        pg = ctx.new_page()
        pg.goto(f"{ZBX}/index.php")
        pg.fill("input[name=name]", "Admin")
        pg.fill("input[name=password]", env["ZBX_ADMIN_PASSWORD"])
        pg.click("button[name=enter], input[name=enter]")
        pg.wait_for_load_state("networkidle")
        for name, url in pages:
            if name.startswith("grafana"):
                g = ctx.new_page()
                g.goto(f"{GRAF}/login")
                g.fill("input[name=user]", "admin")
                g.fill("input[name=password]", env["GRAFANA_ADMIN_PASSWORD"])
                g.keyboard.press("Enter")
                g.wait_for_timeout(3000)
                g.goto(url)
                g.wait_for_timeout(8000)
                g.screenshot(path=OUT + name + ".png")
                continue
            pg.goto(url)
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(1500)
            pg.screenshot(path=OUT + name + ".png", full_page=False)
            print("OK", name)
        b.close()


if __name__ == "__main__":
    main()
