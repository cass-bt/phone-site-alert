# 🚨 Phone Site Alert — Zabbix + Asterisk

Monitora uma página web com **Zabbix** e, quando ela cai, **liga automaticamente**
para um softphone (Linphone/Zoiper) via **Asterisk**, tocando um áudio de alerta
gravado. Tudo offline, em Docker.

```
Zabbix (web scenario)  →  Trigger "site down"  →  Action
        →  script/webhook  →  ARI do Asterisk  →  liga  →  toca "site fora do ar"
```

Os áudios **já vêm prontos** em `sounds/custom/` (pt-BR, formato 8 kHz aceito pelo Asterisk):

| Arquivo | Fala |
|---------|------|
| `site-down.*` | "Atenção. O site monitorado parou de responder..." |
| `alert.*` | "Alerta do sistema de monitoramento. Um serviço está fora do ar..." |
| `recovery.*` | "Serviço restabelecido..." |

Cada um em `.ulaw`, `.gsm` e `.wav` (o Asterisk escolhe o melhor pro codec da chamada).

---

## 📁 Estrutura

```
phone-site-alert/
├── docker-compose.yml        # zabbix-server + web + mariadb + asterisk
├── asterisk_conf/            # configs do Asterisk (PJSIP, ARI, dialplan)
│   ├── pjsip.conf            #   ramal 1000 (softphone)
│   ├── extensions.conf       #   dialplan: contexto [site-alert]
│   ├── ari.conf              #   user 'zabbix' p/ originar chamada
│   ├── http.conf  modules.conf  asterisk.conf
├── sounds/custom/            # áudios prontos (.ulaw/.gsm/.wav)
├── scripts/
│   ├── asterisk_call.sh      # Media type "Script" do Zabbix
│   ├── zabbix_webhook.js     # alternativa: Media type "Webhook"
│   └── test_call.sh          # testa a ligação direto do host
└── shared/                   # volume compartilhado (áudios extras)
```

---

## 🚀 Subir tudo

```bash
docker compose up -d
docker compose ps          # espere todos "running"/"healthy" (~1-2 min)
```

Acessos:

| Serviço | URL | Login |
|---------|-----|-------|
| Zabbix Web | http://localhost:8081 | `Admin` / `zabbix` |
| Asterisk ARI | http://localhost:8088/ari | `zabbix` / `ChangeMe_ARI_123` |
| SIP (softphone) | `localhost:5060` UDP | ramal `1000` / `ChangeMe_1000` |

---

## 📞 Passo 1 — registrar um softphone no ramal 1000

Instale o **Linphone** ou **Zoiper** (no PC ou celular na mesma rede) e configure:

- Usuário/Username: `1000`
- Senha: `ChangeMe_1000`
- Domínio/Domain (SIP server): `IP_DO_HOST` (a máquina que roda o Docker)
- Transporte: UDP, porta 5060

> Se rodar o softphone em outra máquina, troque `localhost` pelo IP do host e
> garanta que as portas 5060/udp e 10000-10010/udp estão acessíveis.

### Teste rápido do áudio (sem Zabbix)
Com o ramal 1000 registrado:
```bash
./scripts/test_call.sh            # liga e toca "site fora do ar"
./scripts/test_call.sh recovery   # liga e toca "recuperado"
```
Ou ligue do próprio softphone para **999** e ouça o alerta.
Se tocou, a parte de telefonia está 100%.

---

## 🌐 Passo 2 — monitorar a página web no Zabbix

No http://localhost:8081 (Admin/zabbix):

**a) Web scenario**
`Data collection → Hosts` → use o host *Zabbix server* (ou crie um host) →
aba **Web scenarios** → *Create web scenario*:
- Name: `Check site`
- Step → *Add*:
  - Name: `home`
  - URL: `https://SEU_SITE.com`
  - Required status codes: `200`
- Update interval: `30s`

**b) Trigger**
`Data collection → Hosts → Triggers → Create trigger`:
- Name: `Site DOWN`
- Severity: `High`
- Expression:
  ```
  last(/Zabbix server/web.test.fail[Check site])<>0
  ```
  (dispara quando qualquer step do cenário falha: timeout, código != 200, etc.)

> Anti-flap (recomendado): exija a falha em N leituras seguidas, p.ex.
> `min(/Zabbix server/web.test.fail[Check site],#3)<>0`

---

## 🔔 Passo 3 — fazer a trigger LIGAR (escolha A **ou** B)

### Opção A — Media type "Script" (usa `scripts/asterisk_call.sh`)
A pasta `scripts/` já está montada no container como *alertscripts*.

1. `Alerts → Media types → Create media type`
   - Name: `Asterisk Call`
   - Type: **Script**
   - Script name: `asterisk_call.sh`
   - Script parameters (nesta ordem):
     - `{ALERT.SENDTO}`
     - `{EVENT.VALUE}`   *(1 = problema → toca "down"; ajuste o script se quiser tratar 0=recovery)*
   - Salvar.

> Obs.: o script já trata `down`/`recovery` pelo 2º argumento. Para mandar
> "recovery" use `{EVENT.RECOVERY.VALUE}` ou crie uma operação de recuperação
> separada passando `recovery`.

2. `Users → Users → Admin → Media` → *Add*:
   - Type: `Asterisk Call`
   - Send to: `1000`   ← o ramal que vai tocar
   - When active: 24x7

3. `Alerts → Actions → Trigger actions → Create action`:
   - Name: `Ligar quando site cair`
   - Conditions: `Trigger severity >= High` (ou trigger = "Site DOWN")
   - **Operations** → *Add*: Send to users `Admin`, via `Asterisk Call`
   - **Default operation step duration**: `1h`  ← evita religar em loop
   - (opcional) **Recovery operations**: notifica quando o site volta

### Opção B — Media type "Webhook" (usa `scripts/zabbix_webhook.js`)
Não depende de binário no container.
1. `Alerts → Media types → Create media type` → Type **Webhook**
   - Cole o conteúdo de `scripts/zabbix_webhook.js` no campo *Script*.
   - Parameters:
     - `ramal` = `{ALERT.SENDTO}`
     - `kind` = `{EVENT.VALUE}`
     - `ari_url` = `http://asterisk:8088/ari/channels`
     - `ari_user` = `zabbix`
     - `ari_pass` = `ChangeMe_ARI_123`
2. Igual à Opção A: associe o media ao usuário `Admin` (Send to = `1000`) e crie a Action.

---

## 🧪 Testar o fluxo completo

Aponte o web scenario para um site que você consiga derrubar (ou use uma URL
inválida de propósito). Quando o Zabbix marcar `web.test.fail<>0`, a trigger
dispara, a action chama o ramal 1000 e você ouve o alerta.

Logs úteis:
```bash
docker logs ssa-asterisk | tail          # viu o originate chegar?
docker logs ssa-zabbix-server | tail      # action/alert executou?
```

---

## ⚠️ Segurança — TROCAR ANTES DE USAR FORA DO LAB

Estes valores são **default de laboratório**:

| Onde | Valor atual | Troque para |
|------|-------------|-------------|
| `ari.conf` user zabbix | `ChangeMe_ARI_123` | senha forte |
| `pjsip.conf` ramal 1000 | `ChangeMe_1000` | senha forte |
| Zabbix Web | `Admin/zabbix` | troque no 1º login |
| MariaDB | `zabbix_pw` / `root_pw` | senhas fortes |
| `ari.conf` | `allowed_origins=*` | restrinja a origem |

Não exponha as portas 8088 (ARI), 5060 (SIP) e 8081 (web) direto na internet —
o ARI sem proteção permite originar chamadas arbitrárias.

---

## 🔧 Regenerar/editar os áudios

Os áudios foram gerados com `espeak-ng` + voz **mbrola br4** (feminina, offline) + `sox`.
Requer: `sudo apt install espeak-ng mbrola mbrola-br4 sox libsox-fmt-all`.
```bash
espeak-ng -v mb-br4 -s 145 "Seu texto aqui" -w /tmp/a.wav
sox /tmp/a.wav -r 8000 -c 1 -t ul  sounds/custom/site-down.ulaw
sox /tmp/a.wav -r 8000 -c 1 -t gsm sounds/custom/site-down.gsm
sox /tmp/a.wav -r 8000 -c 1 -t wav sounds/custom/site-down.wav
```
Para voz ainda mais natural (offline), troque por **Piper TTS**.
```
```
