FROM alpine:3.20
# net-snmp: демон snmpd та утиліти snmpwalk/snmpget
RUN apk add --no-cache net-snmp net-snmp-tools
COPY snmpd.conf /etc/snmp/snmpd.conf
EXPOSE 161/udp
# -f: передній план, -Lo: лог у stdout, -C: не читати типові конфіги (інакше порт реєструється двічі)
CMD ["snmpd", "-f", "-Lo", "-C", "-c", "/etc/snmp/snmpd.conf"]
