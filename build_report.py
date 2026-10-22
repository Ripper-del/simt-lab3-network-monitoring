"""Формує звіт ЛР3 (PDF + DOCX) з файлів evidence/."""
import json
import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "common"))
from report_lib import Report

E = "evidence/"
SH = E + "shots/"
AUTHOR = os.environ.get("LAB_AUTHOR", "Прізвище_Ім'я")
GROUP = os.environ.get("LAB_GROUP", "ІО-00")
r = Report(3, "Моніторинг мережевої інфраструктури. Розгортання Zabbix, збір метрик засобами агента, SNMP та HTTP і візуалізація в Grafana",
           AUTHOR, GROUP, "асистент кафедри ОТ Назар МЕЛЬНИК", "report")
fault = json.load(open(E + "fault.json"))
fmt = lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S")

r.h1("1. Мета і завдання лабораторної роботи")
r.p("Мета: розгорнути систему моніторингу Zabbix у контейнерах, зібрати метрики трьома способами (агент, SNMP, веб-сценарій), "
    "налаштувати тригери для автоматичного виявлення збоїв і візуалізувати стан у Grafana. Об'єкт спостереження — проєкт ЛР1.")
r.p("Виконано основне та додаткове (високий рівень) завдання: власний шаблон з макросом та перевизначенням на вузлі, а також розширення (а) — "
    "автоматичне виявлення контейнерів (low-level discovery).")

r.h1("2. Результати виконання")
r.h2("2.1. Схема системи моніторингу")
r.img(E + "topology.png", "Рис. 1. Мережа моніторингу, мережі проєкту ЛР1 та напрямки збору даних", 15.5)
r.p("Zabbix server збирає дані трьома способами: від Zabbix agent 2 (пасивні перевірки, Docker-плагін через docker.sock у режимі read-only), "
    "по SNMPv2c з контейнера net-device та безагентно веб-сценарієм (HTTP GET до proxy ЛР1). Для останнього zabbix-server додатково підключено "
    "до мережі lab1-frontend як до зовнішньої; сам проєкт ЛР1 не змінюється. Grafana читає дані через API Zabbix окремим користувачем лише для читання.")

r.h2("2.2. Середовище та версії компонентів")
r.step("Версії та стан компонентів", "docker compose ps; zabbix_server -V; postgres --version; /api/health; snmpd -v", E + "04-versions.txt",
       "Zabbix 7.0.10, PostgreSQL 16.15, Grafana 11.6.0, net-snmp 5.9.4 в образі lab3-snmpd:1.0 на alpine:3.20; Docker Engine 28.5.2, Compose v2.40.3.", 12)
r.step("Образи (фіксовані теги)", "docker compose images", E + "04b-images.txt",
       "Усі образи мають конкретні теги, жодного latest.", 12)
r.step("Компоненти запущено", "docker compose ps", E + "01-compose-ps.txt",
       "Усі шість сервісів працюють; на хост опубліковано лише 8081 (веб-інтерфейс Zabbix) і 3000 (Grafana, потрібна для візуалізації).")
r.step("Сервер стартував без помилок", "docker compose logs zabbix-server | tail", E + "02-server-logs.txt",
       "У журналі немає помилок, процеси сервера запущені.")
r.step("Веб-інтерфейс доступний", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8081/", E + "03-web-http.txt",
       "Веб-інтерфейс повертає HTTP 200.")

r.h2("2.3. Структура проєкту")
r.bullets(["docker-compose.yml — Zabbix (server, web, PostgreSQL), agent 2, SNMP-пристрій, Grafana; мережа monitoring 172.30.0.0/24;",
           "snmpd/ (Dockerfile, snmpd.conf) — імітація мережевого пристрою; grafana/provisioning, grafana/dashboards — datasource, плагін і дашборд;",
           "up.sh — розгортання однією командою (генерує паролі в .env, не потрапляє в git) і виклик configure_zabbix.py;",
           "configure_zabbix.py — налаштування Zabbix через API; configure_template.py — власні шаблони; fault_experiment.py — експеримент зі збоєм;",
           "export/*.yaml — експортовані шаблони; grafana/dashboards/lab3.json — експортований дашборд."])
r.p("Паролі (адміністратор Zabbix, Grafana, БД, користувач grafana) генеруються випадково в .env і не включені до звіту та репозиторію. "
    "Community-стрічка навчального стенда lab3comm доступна лише з мережі моніторингу 172.30.0.0/24.")

r.h2("2.4. Виконання пунктів основного завдання")
r.p("Пункт 1 (розгортання в окремій мережі, публікація лише веб-інтерфейсу) підтверджено таблицею вище та docker-compose.yml у розділі 3.")
r.img(SH + "zbx-sysinfo.png", "Рис. 2. Reports → System information: сервер активний, версії сервера та веб-інтерфейсу 7.0.10", 14)
r.p("Пункт 2: пароль адміністратора Admin змінено скриптом через API (user.update) на випадковий; типовий пароль zabbix більше не діє. "
    "Версія БД — PostgreSQL 16.15 (див. таблицю версій), сервер активний (Zabbix server is running: Yes).")
r.step("Пункт 3. Zabbix agent 2 та zabbix_get", "docker compose exec zabbix-server zabbix_get -s zabbix-agent -k agent.ping ...", E + "05-zabbix-get.txt",
       "Агент відповідає на agent.ping (1), повертає навантаження CPU і перелік контейнерів плагіном Docker; доступ до docker.sock змонтовано з прапорцем :ro.", 20)
r.step("Індикатор доступності ZBX/SNMP", "host.get (available)", E + "08-hosts.txt",
       "Для lab1-host інтерфейс агента має available=1 (ZBX активний), для net-device SNMP-інтерфейс має available=1.")
r.img(SH + "zbx-hosts.png", "Рис. 3. Monitoring → Hosts: індикатори ZBX та SNMP активні", 14)
r.step("Пункт 4. Метрики шаблону Linux by Zabbix agent", "Monitoring → Latest data (item.get)", E + "09-latest-linux.txt",
       "Надходять метрики CPU (system.cpu.util), пам'яті (vm.memory.utilization), файлової системи (vfs.fs.dependent.size) та мережевого трафіку (net.if.in).", 20)
r.img(SH + "zbx-latest-linux.png", "Рис. 4. Latest data: завантаження процесора", 13)
r.p("Приклад метрики: елемент «CPU utilization», ключ system.cpu.util, інтервал збору за шаблоном — залежний елемент від 1-хвилинних даних, останнє значення видно на рис. 4.")
r.step("Пункт 5. Docker-плагін: стан контейнера БД", "Latest data для db", E + "10-latest-docker.txt",
       "Елемент docker.container_info.state.status[\"/db\"] (шаблон Docker by Zabbix agent 2) і власний lab1.db.state мають значення running; lab1.db.up=1.", 12)
r.img(SH + "zbx-latest-docker.png", "Рис. 5. Latest data: стан контейнерів ЛР1", 13)
r.step("Пункт 6. Веб-сценарій (безагентна перевірка)", "httptest lab1-app, крок proxy: http://proxy:80/, інтервал 10 с", E + "11-latest-web.txt",
       "Сценарій створив елементи web.test.rspcode (код відповіді, 200), web.test.time (час відповіді), web.test.in, web.test.fail та web.test.error; значення оновлюються кожні 10 с.", 20)
r.img(SH + "zbx-latest-web.png", "Рис. 6. Latest data: елементи веб-сценарію", 13)
r.step("Пункт 7. SNMP-пристрій: перевірка net-snmp", "snmpget/snmpwalk sysName, sysUpTime, ifDescr", E + "06-snmp-manual.txt",
       "OID 1.3.6.1.2.1.1.5.0 — sysName, 1.3.6.1.2.1.1.3.0 — sysUpTime, 1.3.6.1.2.1.1 — system MIB, 1.3.6.1.2.1.2.2.1.2 — ifDescr (перелік інтерфейсів; eth0 має індекс 11).", 18)
r.step("Обмеження доступу SNMP", "snmpget з невірною community; snmpd.conf", E + "07-snmp-acl.txt",
       "З неправильною community відповіді немає (тайм-аут), а rocommunity обмежено підмережею 172.30.0.0/24.", 14)
r.step("Пункт 8. SNMP-метрики в Zabbix", "Latest data net-device", E + "12-latest-snmp.txt",
       "Три метрики отримано по SNMP: час роботи (OID ...1.3.0), стан інтерфейсу ifOperStatus (...2.2.1.8.11) і трафік eth0 (ifHCInOctets/ifHCOutOctets).", 12)
r.img(SH + "zbx-latest-snmp.png", "Рис. 7. Latest data: метрики SNMP-пристрою", 13)

r.h2("Пункт 9. Тригери")
r.table(["Вузол", "Тригер", "Вираз", "Важливість", "Обґрунтування"],
        [["lab1-host", "Застосунок недоступний через проксі",
          "last(/lab1-host/web.test.rspcode[lab1-app,proxy])<>200 or last(/lab1-host/web.test.fail[lab1-app])>0", "High",
          "Код не 200 означає, що сервіс не обслуговує запити; один збій достатньо, бо перевірка раз на 10 с"],
         ["lab1-host", "Контейнер БД зупинено або відсутній",
          "last(/lab1-host/lab1.db.up)=0 or nodata(/lab1-host/lab1.db.up,60s)=1", "High",
          "БД критична для застосунку; nodata 60 с = 6 пропущених інтервалів (контейнер видалено або агент недоступний)"],
         ["net-device", "SNMP-пристрій недоступний", "nodata(/net-device/snmp.uptime,60s)=1", "Average",
          "Немає SNMP-відповіді 60 с (6 інтервалів) — вважаємо пристрій недоступним"],
         ["net-device", "Вхідний трафік eth0 перевищує поріг", "avg(/net-device/snmp.ifin.eth0,1m)>{$SNMP_IN_BPS_MAX}", "Warning",
          "Середнє за 1 хв згладжує піки; поріг 10 Мбіт/с задано макросом на вузлі"]],
       [1.8, 3, 5.2, 1.6, 4.2])
r.step("Налаштовані тригери", "trigger.get", E + "13-triggers.txt",
       "Усі чотири тригери перебувають у стані OK (value 0) до початку експерименту.", 12)

r.h2("Пункт 10. Експеримент зі збоєм")
r.step("Керований збій БД", "python fault_experiment.py (docker compose -p lab1 stop db / start db)", E + "50-fault.txt",
       "Скрипт зупинив БД, дочекався проблем, відновив БД і дочекався автоматичного закриття проблем.", 20)
r.table(["Подія", "Час", "Затримка"],
        [["Зупинка db", fmt(fault["stop"]), "-"],
         [fault["problems"][0]["name"] + " — виникла", fmt(fault["problems"][0]["opened"]), f"{fault['problems'][0]['detect_delay_s']} с"],
         [fault["problems"][1]["name"] + " — виникла", fmt(fault["problems"][1]["opened"]), f"{fault['problems'][1]['detect_delay_s']} с"],
         ["Запуск db", fmt(fault["start"]), "-"],
         [fault["problems"][1]["name"] + " — закрита", fmt(fault["problems"][1]["closed"]), f"{fault['problems'][1]['recovery_delay_s']} с після старту"],
         [fault["problems"][0]["name"] + " — закрита", fmt(fault["problems"][0]["closed"]), f"{fault['problems'][0]['recovery_delay_s']} с після старту"]],
        [8, 2.5, 5])
r.p("Затримка виявлення не є сталою: вона залежить від моменту збою в циклі опитування. HTTP-проблему виявлено за ~1,4 с (збій припав на початок "
    "циклу веб-сценарію з інтервалом 10 с), а проблему БД за ~9,4 с — майже повний інтервал 10 с елемента lab1.db.up. "
    "Обидві затримки не перевищують інтервал опитування плюс час обчислення тригера, тож додаткових пояснень не потребують. "
    "Закриття проблем відбувається автоматично за наступним успішним опитуванням (затримка 1-3 с).")
r.img(SH + "zbx-problems.png", "Рис. 8. Monitoring → Problems: проблеми виникли та закрито автоматично (Recovery time)", 14)

r.h2("Пункт 11. Grafana")
r.p("Grafana розгорнуто в мережі моніторингу з плагіном alexanderzobnin-zabbix-app 6.4.1. Datasource підключено до API Zabbix окремим користувачем grafana, "
    "який входить у групу grafana-readonly з правом лише читання (permission 2) на групу вузлів Lab3. Перевірено: користувач бачить обидва вузли, "
    "а спроба host.update завершується помилкою «No permissions to call host.update».")
r.img(SH + "grafana-dashboard.png", "Рис. 9. Дашборд Grafana з періодом збою (db зупинено, HTTP-код 5xx)", 15.5)
r.bullets(["Доступність застосунку — код відповіді веб-сценарію у вигляді state-timeline; червоний інтервал відповідає збою БД (503);",
           "Час відповіді застосунку — відповідь кроку веб-сценарію в секундах;",
           "Стан контейнерів ЛР1 — запущено/зупинено (1/0) для db, proxy та app; червоний відрізок db збігається з експериментом;",
           "Трафік eth0 SNMP-пристрою — вхідний і вихідний трафік у біт/с, отриманий по SNMP."])
r.p("Дашборд експортовано у grafana/dashboards/lab3.json, діапазон часу охоплює 2 хв до збою і 2 хв після відновлення.")

r.h2("2.5. Таблиця налаштованих елементів даних")
r.table(["Вузол", "Тип", "Ключ", "Інтервал"],
        [["lab1-host", "Zabbix agent", "docker.container_info[db,full] (+ залежні lab1.db.state, lab1.db.up)", "10 с"],
         ["lab1-host", "Web (httptest)", "web.test.rspcode[lab1-app,proxy], web.test.time[lab1-app,proxy,resp], web.test.fail[lab1-app]", "10 с"],
         ["lab1-host", "Simple check", "net.tcp.service.perf[http,proxy,80] (власний шаблон)", "10 с"],
         ["lab1-host", "Calculated", "lab3.rt.ms (власний шаблон)", "10 с"],
         ["net-device", "SNMP agent", "snmp.uptime (1.3.6.1.2.1.1.3.0)", "10 с"],
         ["net-device", "SNMP agent", "snmp.ifoper.eth0 (1.3.6.1.2.1.2.2.1.8.11)", "10 с"],
         ["net-device", "SNMP agent", "snmp.ifin.eth0 / snmp.ifout.eth0 (ifHCInOctets/OutOctets .11)", "10 с"]],
        [2.2, 2.8, 9.3, 1.8])

r.h2("2.6. Додаткове завдання (високий рівень)")
r.p("Власний шаблон «Lab3 HTTP template» містить елемент net.tcp.service.perf[http,proxy,80], обчислюваний елемент lab3.rt.ms "
    "(last(//net.tcp.service.perf[http,proxy,80])*1000), макрос {$LAB3.RT.MAX.MS}=500 та тригер "
    "avg(/Lab3 HTTP template/lab3.rt.ms,1m)>{$LAB3.RT.MAX.MS}. Шаблон застосовано до lab1-host.")
r.step("Перевизначення макросу на рівні вузла", "python configure_template.py macro 1; потім macro reset", E + "20-template-override.txt",
       "З макросом шаблону (500 мс) тригер у стані OK. Після перевизначення на вузлі до 1 мс вираз став avg(...)>1, тригер перейшов у PROBLEM; після скидання макросу повернувся 500 і проблему закрито. Отже, поведінка тригера змінюється без редагування шаблону.", 30)
r.p("Розширення (а) — low-level discovery. Обґрунтування вибору: LLD найкраще відповідає динаміці контейнерного середовища, де кількість реплік змінюється "
    "без участі адміністратора, а ручне додавання елементів і тригерів для кожної репліки неприйнятне.")
r.step("Автовиявлення контейнерів: нова репліка app", "docker compose -p lab1 up -d --scale app=2; Latest data lab3.container.up", E + "21-lld.txt",
       "Правило виявлення docker.containers.discovery[true] (інтервал 30 с, фільтр за {#NAME}) створило прототипи: після масштабування з'явились елемент lab3.container.up[/lab1-app-2] і тригер «контейнер /lab1-app-2 зупинено» без ручного налаштування.", 30)
r.img(SH + "zbx-latest-lld.png", "Рис. 10. Latest data: елементи, створені правилом виявлення, включно з реплікою lab1-app-2", 13)

r.h1("3. Конфігураційні файли")
for name in ["docker-compose.yml", "snmpd/snmpd.conf", "snmpd/Dockerfile", "up.sh", "grafana/provisioning/datasources/zabbix.yml", "export/lab3_http_template.yaml"]:
    r.code(open(name, encoding="utf-8").read().rstrip(), name)

r.h1("4. Висновки")
r.p("Розгорнуто систему моніторингу Zabbix 7.0.10 з Grafana в контейнерах однією командою up.sh; моніторинг зовнішній щодо проєкту ЛР1. "
    "Налаштовано три способи збору даних, чотири тригери та підтверджено автоматичне виявлення і закриття збоїв: затримка виявлення не перевищила інтервал опитування. "
    "Власний шаблон із макросом дозволив змінювати поріг на рівні вузла, а low-level discovery автоматично охопив нову репліку застосунку.")
r.p("Порівняння способів збору даних:")
r.table(["Критерій", "Zabbix agent", "SNMP", "Веб-сценарій"],
        [["Що потрібно на цільовому вузлі", "Встановлений агент і доступ до даних (наприклад, docker.sock)", "SNMP-агент (snmpd) і налаштована community/ACL", "Нічого: достатньо доступного URL"],
         ["Хто ініціює обмін", "Сервер (пасивні) або агент (активні перевірки)", "Сервер опитує пристрій (polling); можливі trap", "Сервер виконує HTTP-запити"],
         ["Затримка виявлення збою", "До інтервалу опитування + обчислення тригера (тут ~9 с при 10 с)", "До інтервалу опитування + тайм-аути SNMP", "До інтервалу сценарію (тут 10 с; виявлено за 1,4 с)"],
         ["Придатність для мережевого обладнання", "Низька: на комутатор агент зазвичай не встановити", "Висока: SNMP є майже на всьому обладнанні", "Лише для перевірки доступності сервісів, не пристрою"]],
        [3.5, 4.5, 4.5, 4.5])
r.p("Висновок: агент доцільний для серверів і контейнерних хостів (глибокі метрики), SNMP — для мережевого обладнання, веб-сценарій — для оцінки "
    "доступності сервісу очима користувача. Найкраще їх поєднувати.")
r.p("Підпис виконавця: ____________      Підпис викладача: ____________")
print(r.build())
