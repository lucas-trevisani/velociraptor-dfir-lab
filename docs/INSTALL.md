# Instalacao

1. Copie `.env.example` para `.env` e substitua todos os segredos.
2. Gere chaves RSA e AES com `scripts/generate_keys.sh`.
3. Copie o conteudo de `secrets/aes_key_base64.txt` para `AES_KEY_BASE64`.
4. Na VPS, execute `scripts/audit_vps.sh` antes de instalar qualquer pacote.
5. Confirme que as portas `18443`, `18080` e `25432` estao livres.
6. Suba somente este compose: `docker compose -f docker/docker-compose.yml up -d --build`.
7. Crie o admin: `docker compose -f docker/docker-compose.yml exec api python -m api.app.seed_admin`.

Nao edite configs existentes de nginx, caddy, apache, systemd ou Docker sem uma janela planejada.
