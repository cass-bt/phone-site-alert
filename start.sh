#!/usr/bin/env bash
# ============================================================
# Sobe a stack E reinicia o Linphone limpo, garantindo que o
# ramal 1000 registre fresco (com qualify) toda vez.
#
# Por que reiniciar o Linphone junto? Asterisk roda em container
# atrás do NAT do Docker. Quando os containers reiniciam, o
# contato SIP registrado morre e o Linphone (UDP) só re-registra
# ~1h depois. Reabrir o Linphone força um registro novo na hora.
# ============================================================
set -e
cd "$(dirname "$0")"

APPIMAGE="${LINPHONE_APPIMAGE:-$HOME/Apps/Linphone.AppImage}"
RAMAL=1000

echo "==> Subindo a stack..."
docker compose up -d

echo "==> Aguardando Asterisk ficar saudável..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' ssa-asterisk 2>/dev/null)" = "healthy" ]; do sleep 2; done
echo "    Asterisk OK."

if [ -f "$APPIMAGE" ]; then
  echo "==> Reiniciando o Linphone (registro fresco)..."
  pkill -9 -f Linphone.AppImage 2>/dev/null || true
  sleep 2
  DISPLAY="${DISPLAY:-:0}" nohup "$APPIMAGE" >/tmp/linphone.log 2>&1 &
  disown 2>/dev/null || true

  echo "==> Aguardando o ramal $RAMAL registrar..."
  for i in $(seq 1 15); do
    sleep 2
    st=$(docker exec ssa-asterisk asterisk -rx "pjsip show contacts" 2>/dev/null | grep -i "$RAMAL/" | grep -oE "Avail|NonQual|Unavail" || true)
    [ -n "$st" ] && { echo "    Ramal $RAMAL registrado (status: $st)."; break; }
  done
else
  echo "!! Linphone AppImage não encontrado em $APPIMAGE — abra o softphone na mão."
fi

echo ""
echo "==> Pronto."
echo "   Zabbix:  http://localhost:8081  (Admin/zabbix)"
echo "   Testar:  docker compose stop website   (liga em ~30s)"
echo "   Voltar:  docker compose start website"
