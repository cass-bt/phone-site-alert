#!/usr/bin/env python3
"""Configura no Zabbix (via API) o monitoramento do site + ligação automática.
Idempotente: remove objetos com o mesmo nome antes de recriar."""
import json, urllib.request, sys

API = "http://localhost:8081/api_jsonrpc.php"
USER, PASS = "Admin", "zabbix"

HOST_NAME   = "Zabbix server"          # host onde roda o web scenario
SCEN_NAME   = "Check site"             # nome do web scenario
TARGET_URL  = "http://website/"        # site monitorado (container nginx)
MEDIA_NAME  = "Asterisk Call"
ACTION_NAME = "Ligar quando site cair"
RAMAL       = "1000"

_token = None
def call(method, params, auth=True):
    body = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json-rpc"})
    if auth and _token:
        req.add_header("Authorization", "Bearer " + _token)
    r = json.loads(urllib.request.urlopen(req, timeout=15).read())
    if "error" in r:
        raise RuntimeError(f"{method}: {r['error']['data']}")
    return r["result"]

# 1) login
_token = call("user.login", {"username": USER, "password": PASS}, auth=False)
print("[+] login ok")

# 2) host + admin user ids
hostid = call("host.get", {"filter": {"host": HOST_NAME}, "output": ["hostid"]})[0]["hostid"]
adminid = call("user.get", {"filter": {"username": "Admin"}, "output": ["userid"]})[0]["userid"]
print(f"[+] host '{HOST_NAME}'={hostid}  admin={adminid}")

# --- limpa execuções anteriores (idempotência) ---
for a in call("action.get", {"filter": {"name": ACTION_NAME}, "output": ["actionid"]}):
    call("action.delete", [a["actionid"]])
for t in call("httptest.get", {"filter": {"name": SCEN_NAME}, "output": ["httptestid"]}):
    call("httptest.delete", [t["httptestid"]])
for m in call("mediatype.get", {"filter": {"name": MEDIA_NAME}, "output": ["mediatypeid"]}):
    call("mediatype.delete", [m["mediatypeid"]])
print("[+] limpeza de objetos antigos ok")

# 3) web scenario — checa o site a cada 30s, exige HTTP 200
httptestid = call("httptest.create", {
    "name": SCEN_NAME, "hostid": hostid, "delay": "30s", "retries": 1,
    "steps": [{
        "name": "home", "url": TARGET_URL, "status_codes": "200", "no": 1,
        "timeout": "10s", "required": ""
    }],
})["httptestids"][0]
print(f"[+] web scenario criado (httptestid={httptestid})")

# 4) trigger — dispara quando o passo do cenário falha
expr = f"last(/{HOST_NAME}/web.test.fail[{SCEN_NAME}])<>0"
triggerid = call("trigger.create", {
    "description": "Site DOWN: {HOST.NAME}", "expression": expr,
    "priority": 4,  # High
    "manual_close": 1,
})["triggerids"][0]
print(f"[+] trigger criada (triggerid={triggerid})")

# 5) media type WEBHOOK que liga pro Asterisk via ARI api_key
webhook_js = r"""
var p = JSON.parse(value);
var exten = (p.event_value === '0') ? 'recovery' : 'alert';
var url = p.ari_url + '?api_key=' + encodeURIComponent(p.ari_user) + ':' + encodeURIComponent(p.ari_pass);
var req = new HttpRequest();
req.addHeader('Content-Type: application/json');
var body = JSON.stringify({endpoint: 'PJSIP/' + p.ramal, extension: exten, context: 'site-alert', priority: 1});
var resp = req.post(url, body);
Zabbix.log(4, '[asterisk] status=' + req.getStatus() + ' resp=' + resp);
if (req.getStatus() < 200 || req.getStatus() >= 300) { throw 'ARI status ' + req.getStatus() + ': ' + resp; }
return 'OK';
"""
mediatypeid = call("mediatype.create", {
    "name": MEDIA_NAME, "type": 4,  # 4 = Webhook
    "status": 0,                     # 0 = habilitado (default da API é desabilitado!)
    "script": webhook_js,
    "parameters": [
        {"name": "ramal",       "value": "{ALERT.SENDTO}"},
        {"name": "event_value", "value": "{EVENT.VALUE}"},
        {"name": "ari_url",     "value": "http://asterisk:8088/ari/channels"},
        {"name": "ari_user",    "value": "zabbix"},
        {"name": "ari_pass",    "value": "ChangeMe_ARI_123"},
    ],
    "message_templates": [
        {"eventsource": 0, "recovery": 0, "subject": "Site DOWN", "message": "{EVENT.NAME}"},
        {"eventsource": 0, "recovery": 1, "subject": "Site OK",   "message": "{EVENT.NAME}"},
    ],
})["mediatypeids"][0]
print(f"[+] media type webhook criado (mediatypeid={mediatypeid})")

# 6) adiciona a mídia ao usuário Admin (Send to = ramal)
call("user.update", {
    "userid": adminid,
    "medias": [{
        "mediatypeid": mediatypeid, "sendto": RAMAL,
        "active": 0, "severity": 63, "period": "1-7,00:00-24:00",
    }],
})
print(f"[+] mídia adicionada ao Admin (sendto={RAMAL})")

# 7) action — quando a trigger dispara, manda mensagem (=liga) pro Admin
call("action.create", {
    "name": ACTION_NAME, "eventsource": 0, "status": 0, "esc_period": "1h",
    "filter": {"evaltype": 0, "conditions": [
        {"conditiontype": 2, "operator": 0, "value": triggerid},  # trigger = nossa trigger
    ]},
    "operations": [{
        "operationtype": 0, "esc_period": "0", "esc_step_from": 1, "esc_step_to": 1,
        "opmessage": {"default_msg": 1, "mediatypeid": mediatypeid},
        "opmessage_usr": [{"userid": adminid}],
    }],
    "recovery_operations": [{
        "operationtype": 0,
        "opmessage": {"default_msg": 1, "mediatypeid": mediatypeid},
        "opmessage_usr": [{"userid": adminid}],
    }],
})
print(f"[+] action '{ACTION_NAME}' criada")
print("\n=== TUDO CONFIGURADO ===")
print("Para testar:  docker compose stop website   (espera ~1min -> liga)")
print("Para voltar:  docker compose start website")
