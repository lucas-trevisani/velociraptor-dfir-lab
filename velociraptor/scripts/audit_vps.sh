#!/usr/bin/env bash
set -euo pipefail

OUT="vps-audit-$(date +%Y%m%d-%H%M%S).txt"
{
  echo "# VPS audit $(date -Is)"
  echo "## Host"
  hostnamectl || true
  echo "## Listening ports"
  ss -tulpn || true
  echo "## Docker containers"
  docker ps -a || true
  echo "## Docker compose projects"
  docker compose ls || true
  echo "## systemd services"
  systemctl list-units --type=service --state=running || true
  echo "## Reverse proxies"
  systemctl status nginx --no-pager || true
  systemctl status caddy --no-pager || true
  systemctl status apache2 --no-pager || true
  httpd -S || true
  nginx -T || true
  caddy list-modules || true
  echo "## Databases"
  systemctl status postgresql --no-pager || true
  systemctl status mysql --no-pager || true
  docker ps --format '{{.Names}} {{.Image}} {{.Ports}}' | grep -Ei 'postgres|mysql|mariadb|mongo|redis' || true
  echo "## Certificates"
  find /etc/letsencrypt /etc/ssl /var/lib/caddy -maxdepth 3 -type f 2>/dev/null || true
} | tee "$OUT"

echo "Audit saved to $OUT"

