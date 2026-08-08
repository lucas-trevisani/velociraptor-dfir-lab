# API

Endpoints principais:

- `POST /api/auth/login`: autentica usuario e retorna JWT.
- `POST /api/client/register`: registra HWID e aplica limite de dispositivos.
- `POST /api/license/check`: valida licenca, dispositivo e Hunts permitidas.
- `POST /api/hunt/download`: retorna manifesto com hash SHA256, assinatura RSA e URLs.
- `POST /api/result/upload`: recebe resultado e registra hash.
- `GET /api/version`: versoes de API e launcher minimo.
- `GET /api/update`: versoes de launcher, regras e assinaturas.

Rotas administrativas exigem usuario `admin` via JWT.

