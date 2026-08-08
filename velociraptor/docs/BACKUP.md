# Backup

Backup minimo:

- Dump PostgreSQL diario.
- Copia criptografada de `storage/hunts`.
- Copia criptografada de `storage/results`.
- Copia offline de `secrets/license_private.pem`.

Restore deve ser testado em VPS separada antes de qualquer procedimento em producao.

