// ============================================================
// Media type "Webhook" do Zabbix (alternativa ao Script .sh).
// Cole este código em: Alerts > Media types > Create > Webhook.
// Não precisa de curl/binário no container — usa o HttpRequest nativo.
//
// Parâmetros do webhook (aba Parameters):
//   ramal      = 1000
//   kind       = {EVENT.VALUE}        (1 = problema, 0 = recuperado)
//   ari_url    = http://asterisk:8088/ari/channels
//   ari_user   = zabbix
//   ari_pass   = ChangeMe_ARI_123
// ============================================================
try {
    var p = JSON.parse(value);
    var exten = (p.kind === '0') ? 'recovery' : 'alert';

    var body = JSON.stringify({
        endpoint:  'PJSIP/' + p.ramal,
        extension: exten,
        context:   'site-alert',
        priority:  1
    });

    var req = new HttpRequest();
    req.addHeader('Content-Type: application/json');
    req.addHeader('Authorization: Basic ' + btoa(p.ari_user + ':' + p.ari_pass));

    var resp = req.post(p.ari_url, body);
    Zabbix.log(4, '[asterisk webhook] status=' + req.getStatus() + ' resp=' + resp);

    if (req.getStatus() < 200 || req.getStatus() >= 300) {
        throw 'ARI retornou status ' + req.getStatus() + ': ' + resp;
    }
    return 'OK';
} catch (err) {
    Zabbix.log(3, '[asterisk webhook] erro: ' + err);
    throw 'Falha ao originar chamada: ' + err;
}
