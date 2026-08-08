# Seguranca

Implementado na base:

- JWT com sessoes revogaveis.
- Rate limit por IP.
- HWID com hash no banco.
- Limite de dispositivos por licenca.
- Hash SHA256 de Hunts e resultados.
- Assinatura RSA de Hunts.
- Nonce nos fluxos de cliente para base anti replay.
- Remocao de diretorio temporario apos execucao.

Recomendado para producao:

- TLS com certificado valido.
- HSM ou secret manager para chave RSA privada.
- Empacotar launcher com assinatura de codigo.
- Guardar nonces usados com TTL em Redis/PostgreSQL.
- Executar Velociraptor em sandbox com permissoes minimas.
- Auditar todos os uploads e downloads por dispositivo.
- Ativar WAF/rate limiting tambem no proxy.

