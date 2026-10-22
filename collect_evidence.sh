#!/usr/bin/env bash
# Збір виводів команд ЛР3 у evidence/*.txt (експеримент зі збоєм: fault_experiment.py -> evidence/50-fault.txt)
cd "$(dirname "$0")"
E=evidence; mkdir -p $E
PY=.venv/bin/python
LAB1="docker compose -f ../LR1/docker-compose.yml -p lab1"
# запис команди та її виводу у файл
run() { local f="$E/$1.txt"; shift; { echo "\$ $*"; eval "$@" 2>&1; } > "$f"; }

run 01-compose-ps "docker compose ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
run 02-server-logs "docker compose logs zabbix-server | tail -8"
run 03-web-http "curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8081/"
run 04-versions "docker compose exec -T zabbix-server zabbix_server -V | head -1; docker compose exec -T zabbix-db postgres --version; curl -s http://localhost:3000/api/health | tr -d '\n '; echo; docker compose exec -T net-device snmpd -v | head -2; docker compose images"
run 05-zabbix-get "for k in agent.ping 'system.cpu.load[all,avg1]'; do echo \"== \$k\"; docker compose exec -T zabbix-server zabbix_get -s zabbix-agent -k \"\$k\"; done; docker compose exec -T zabbix-server zabbix_get -s zabbix-agent -k 'docker.containers.discovery[false]' | head -c 700; echo"
run 06-snmp-manual "N='docker run --rm --network lab3-monitoring lab3-snmpd:1.0'; \$N snmpget -v2c -c lab3comm net-device 1.3.6.1.2.1.1.5.0 1.3.6.1.2.1.1.3.0; \$N snmpwalk -v2c -c lab3comm net-device 1.3.6.1.2.1.1; \$N snmpwalk -v2c -c lab3comm net-device 1.3.6.1.2.1.2.2.1.2"
run 07-snmp-acl "docker run --rm --network lab3-monitoring lab3-snmpd:1.0 snmpget -v2c -c wrongcomm -t1 -r1 net-device 1.3.6.1.2.1.1.5.0; echo 'rocommunity ... 172.30.0.0/24 -> лише мережа моніторингу'; grep -v '^#' snmpd/snmpd.conf"
run 08-hosts "$PY zbx_query.py hosts | grep -v 'Zabbix server'"
run 09-latest-linux "$PY zbx_query.py latest 'system.cpu.util' 'vm.memory.utilization' 'vfs.fs.dependent.size[/etc/hosts' 'net.if.in[' | grep -E 'system.cpu.util |vm.memory.utilization|pused|net.if.in' | head -12"
run 10-latest-docker "$PY zbx_query.py latest 'lab1.db' 'docker.container_info[db' 'docker.container_info.state.status[\"/db\"]'"
run 11-latest-web "$PY zbx_query.py latest 'web.test'"
run 12-latest-snmp "$PY zbx_query.py latest 'snmp.' | grep net-device"
run 13-triggers "$PY zbx_query.py triggers | grep -E 'LR1:|SNMP:' "

# власний шаблон: перевизначення макросу на рівні вузла
{
  echo "\$ ТРИГЕР ШАБЛОНУ ДО ПЕРЕВИЗНАЧЕННЯ МАКРОСУ ({\$LAB3.RT.MAX.MS}=500 з шаблону)"
  $PY zbx_query.py triggers | grep 'Lab3:'
  echo; echo "\$ python configure_template.py macro 1   # перевизначення на вузлі lab1-host"
  $PY configure_template.py macro 1
} > $E/20-template-override.txt 2>&1
sleep 100
{
  echo "\$ ПІСЛЯ ПЕРЕВИЗНАЧЕННЯ (через ~100 с)"
  $PY zbx_query.py triggers | grep 'Lab3:'
  $PY zbx_query.py problems | grep 'Lab3:'
  echo; echo "\$ python configure_template.py macro reset"
  $PY configure_template.py macro reset
} >> $E/20-template-override.txt 2>&1
sleep 100
{ echo "\$ ПІСЛЯ ПОВЕРНЕННЯ МАКРОСУ"; $PY zbx_query.py triggers | grep 'Lab3:'; $PY zbx_query.py problems | grep 'Lab3:'; } >> $E/20-template-override.txt 2>&1

# LLD: додаткова репліка app
{
  echo "\$ ДО МАСШТАБУВАННЯ"; $PY zbx_query.py latest 'lab3.container.up' | cut -c1-120
  echo; echo "\$ docker compose -p lab1 up -d --scale app=2 --no-recreate"
  $LAB1 up -d --scale app=2 --no-recreate 2>&1 | tail -3
} > $E/21-lld.txt 2>&1
sleep 75
{
  echo; echo "\$ ПІСЛЯ МАСШТАБУВАННЯ (через 75 с, LLD кожні 30 с)"
  $PY zbx_query.py latest 'lab3.container.up' | cut -c1-120
  $PY zbx_query.py triggers | grep 'Lab3: контейнер'
} >> $E/21-lld.txt 2>&1
echo done
