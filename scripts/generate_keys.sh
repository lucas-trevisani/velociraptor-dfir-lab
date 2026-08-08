#!/usr/bin/env bash
set -euo pipefail
mkdir -p secrets
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out secrets/license_private.pem
openssl rsa -pubout -in secrets/license_private.pem -out secrets/license_public.pem
openssl rand -base64 32 > secrets/aes_key_base64.txt
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
  -keyout secrets/api_tls.key \
  -out secrets/api_tls.crt \
  -subj "/CN=YOUR_VPS_IP" \
  -addext "subjectAltName=IP:YOUR_VPS_IP,DNS:localhost"
chmod 600 secrets/license_private.pem
chmod 600 secrets/api_tls.key
chmod 644 secrets/license_public.pem
chmod 644 secrets/api_tls.crt
chmod 600 secrets/aes_key_base64.txt
echo "Set AES_KEY_BASE64 to the content of secrets/aes_key_base64.txt"
