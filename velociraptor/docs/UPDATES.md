# Atualizacoes

O launcher chama:

- `GET /api/version` para versao minima.
- `GET /api/update` para versoes de launcher, regras e assinaturas.
- `POST /api/license/check` para renovacao periodica da autorizacao.
- `POST /api/hunt/download` para novas Hunts autorizadas.

Para atualizacao automatica real, publique binarios assinados do launcher e valide assinatura antes de substituir o executavel local.

