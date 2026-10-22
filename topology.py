"""Схема системи моніторингу ЛР3."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def box(ax, x, y, w, h, text, fc="#fff", fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec="black", lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, p1, p2, label, color="#336", off=(0, 0.12)):
    ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="->", lw=1.5, color=color))
    ax.text((p1[0] + p2[0]) / 2 + off[0], (p1[1] + p2[1]) / 2 + off[1], label, fontsize=8, color=color, ha="center")


fig, ax = plt.subplots(figsize=(11, 6.4))
ax.set_xlim(0, 11); ax.set_ylim(0, 6.4); ax.axis("off")
ax.add_patch(FancyBboxPatch((0.2, 2.4), 6.6, 3.8, boxstyle="round,pad=0.02", fc="#eef3ff", ec="#336", lw=1.5))
ax.text(0.4, 5.95, "Мережа моніторингу lab3-monitoring 172.30.0.0/24", fontsize=10, weight="bold")
box(ax, 0.5, 3.9, 1.8, 1.1, "zabbix-db\nPostgreSQL 16")
box(ax, 2.9, 3.9, 1.8, 1.1, "zabbix-server\n10051", "#dde8ff")
box(ax, 5.1, 4.6, 1.5, 0.9, "zabbix-agent\nagent 2 :10050", "#e0ffe0")
box(ax, 5.1, 2.9, 1.5, 0.9, "net-device\nsnmpd 161/udp", "#e0ffe0")
box(ax, 0.5, 2.7, 1.8, 0.9, "zabbix-web\n8081 -> 8080", "#dde8ff")
box(ax, 2.9, 2.7, 1.8, 0.9, "grafana :3000\nplugin Zabbix", "#ffe8cc")
ax.add_patch(FancyBboxPatch((0.2, 0.2), 10.6, 1.9, boxstyle="round,pad=0.02", fc="#fff3e0", ec="#a60", lw=1.5))
ax.text(0.4, 1.85, "Проєкт ЛР1 (не змінюється); мережа lab1-frontend підключена до zabbix-server", fontsize=10, weight="bold")
box(ax, 0.6, 0.45, 2.2, 0.9, "proxy :80", "#fff")
box(ax, 3.4, 0.45, 2.2, 0.9, "app :8000", "#fff")
box(ax, 6.2, 0.45, 2.2, 0.9, "db (redis) :6379", "#fff")
box(ax, 8.1, 3.4, 2.6, 1.2, "Docker Engine\n/var/run/docker.sock (ro)", "#eeeeee")
arrow(ax, (2.9, 4.45), (2.3, 4.45), "БД", off=(0, 0.1))
arrow(ax, (4.7, 4.7), (5.1, 5.0), "", off=(0, 0))
ax.text(4.8, 5.35, "агент (passive)", fontsize=8, color="#336", ha="center")
arrow(ax, (4.7, 4.1), (5.1, 3.5), "", off=(0, 0))
ax.text(4.95, 3.75, "SNMPv2c", fontsize=8, color="#336", ha="center")
arrow(ax, (3.8, 3.6), (3.8, 3.9), "", off=(0, 0))
ax.text(4.35, 3.72, "API (ro)", fontsize=8, color="#336", ha="center")
arrow(ax, (3.8, 3.9), (1.7, 1.35), "", color="#a60", off=(0, 0))
ax.text(3.3, 2.15, "веб-сценарій: HTTP GET proxy:80", fontsize=8, color="#a60", ha="left")
arrow(ax, (6.6, 5.0), (8.1, 4.3), "", color="#555", off=(0, 0))
ax.text(7.45, 4.9, "стан контейнерів", fontsize=8, color="#555", ha="center")
arrow(ax, (9.4, 3.4), (7.3, 1.35), "", color="#555", off=(0, 0))
ax.text(9.0, 2.5, "керує контейнерами ЛР1", fontsize=8, color="#555", ha="center")
plt.savefig("evidence/topology.png", dpi=150, bbox_inches="tight")
