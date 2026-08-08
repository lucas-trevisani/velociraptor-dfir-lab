# Deploy seguro na VPS YOUR_VPS_IP

Este projeto deve ser instalado como pilha independente. O compose usa nomes fixos `velo-license-*`, volume proprio e portas altas.

Checklist obrigatorio antes do deploy:

- Revisar portas com `ss -tulpn`.
- Revisar containers com `docker ps -a`.
- Revisar projetos com `docker compose ls`.
- Revisar systemd com `systemctl list-units --type=service`.
- Revisar nginx/caddy/apache sem sobrescrever arquivos.
- Revisar PostgreSQL/MySQL/Redis existentes.
- Revisar certificados em `/etc/letsencrypt`, `/etc/ssl` e `/var/lib/caddy`.

HTTPS pode ser terminado por um novo vhost dedicado ou por TLS direto em proxy separado. Nunca altere vhosts existentes sem backup e revisao.

