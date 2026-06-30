#!/bin/bash
# Testa a ligação DIRETO do host, sem depender do Zabbix.
# Use depois de 'docker compose up -d' e com o softphone registrado no ramal 1000.
#
#   ./scripts/test_call.sh            -> toca o alerta de "site down"
#   ./scripts/test_call.sh recovery   -> toca o alerta de "recuperado"

RAMAL="${RAMAL:-1000}"
ARI_USER="${ARI_USER:-zabbix}"
ARI_PASS="${ARI_PASS:-ChangeMe_ARI_123}"
KIND="${1:-down}"

[ "$KIND" = "recovery" ] && EXTEN="recovery" || EXTEN="alert"

curl -s -u "${ARI_USER}:${ARI_PASS}" \
  -X POST "http://localhost:8088/ari/channels" \
  -H "Content-Type: application/json" \
  -d "{\"endpoint\":\"PJSIP/${RAMAL}\",\"extension\":\"${EXTEN}\",\"context\":\"site-alert\",\"priority\":1}" \
  && echo "" && echo "[+] Chamada originada para o ramal ${RAMAL} (exten=${EXTEN})"
