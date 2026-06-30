#!/bin/sh
# ============================================================
# asterisk_call.sh  —  Media type "Script" do Zabbix
#
# Uso:   asterisk_call.sh  <ramal>  <down|recovery>
#   $1 = ramal de destino (ex: 1000)  -> {ALERT.SENDTO}
#   $2 = tipo do evento: "down" (default) ou "recovery"
#
# Origina uma chamada via ARI do Asterisk. O dialplan atende e
# toca o áudio gravado (site-down / recovery).
# ============================================================

ASTERISK_HOST="${ASTERISK_HOST:-asterisk:8088}"
ARI_USER="${ARI_USER:-zabbix}"
ARI_PASS="${ARI_PASS:-ChangeMe_ARI_123}"

RAMAL="${1:-1000}"
KIND="${2:-down}"

if [ "$KIND" = "recovery" ]; then
  EXTEN="recovery"
else
  EXTEN="alert"
fi

URL="http://${ASTERISK_HOST}/ari/channels"
BODY="{\"endpoint\":\"PJSIP/${RAMAL}\",\"extension\":\"${EXTEN}\",\"context\":\"site-alert\",\"priority\":1}"

if command -v curl >/dev/null 2>&1; then
  curl -s -u "${ARI_USER}:${ARI_PASS}" -X POST "$URL" \
       -H "Content-Type: application/json" -d "$BODY"
else
  # fallback: busybox wget (Alpine). Auth via querystring api_key não serve aqui,
  # então passamos basic-auth no header manualmente.
  AUTH=$(printf '%s:%s' "$ARI_USER" "$ARI_PASS" | base64 | tr -d '\n')
  wget -q -O - \
       --header="Authorization: Basic ${AUTH}" \
       --header="Content-Type: application/json" \
       --post-data="$BODY" "$URL"
fi

echo "[asterisk_call] ramal=${RAMAL} exten=${EXTEN} -> ${URL}"
exit 0
