# Velociraptor DFIR Management Platform

Security-focused platform for controlled Velociraptor deployments, endpoint authentication, Hunt distribution, result collection, auditing, and centralized administration.

> Portfolio/lab project. Configuration examples use placeholders and must be adapted before deployment. Do not use against systems without authorization.

## Architecture

```text
Windows Endpoint / Launcher
          |
          | HTTPS + JWT
          v
      FastAPI API
   /       |        \
Auth     Hunts     Results
          |
          v
     PostgreSQL
          ^
          |
    React Admin Panel

Infrastructure: Linux VPS + Docker Compose
```

## Security Features

- JWT-based authentication and revocable sessions
- Role-based administrative access
- Rate limiting
- RSA signing for Hunt integrity/authenticity
- SHA-256 integrity checks
- Encrypted data handling support
- Device identification and controlled licensing
- Audit logging
- TLS-ready API deployment
- Isolated secrets and runtime storage

## Technology Stack

- Python / FastAPI
- React / Vite
- PostgreSQL
- Docker / Docker Compose
- Linux VPS
- Velociraptor
- JWT, RSA, SHA-256 and TLS

## Repository Structure

- `api/` - FastAPI backend, authentication, licenses, devices, Hunts, results and audit logs.
- `panel/` - React administrative interface.
- `launcher/` - Python launcher for authenticated retrieval/execution workflows and result upload.
- `database/` - SQL schema.
- `docker/` - Container definitions and Docker Compose deployment.
- `scripts/` - VPS auditing and key-generation utilities.
- `docs/` - Installation, deployment, operations, backup, API, database and security notes.

## Quick Start

1. Copy `.env.example` to `.env` and replace every placeholder with your own values.
2. Generate deployment keys with `scripts/generate_keys.sh` in a controlled environment.
3. Review `docs/SECURITY.md` and `docs/DEPLOY.md`.
4. Configure `YOUR_VPS_IP` / hostnames for your own lab environment.
5. Deploy using the Docker Compose configuration.

Never commit `.env`, generated keys, certificates, production IP addresses, tokens, credentials, collected endpoint data, or other secrets.

## Documentation

See the `docs/` directory for installation, deployment, operations, backup, API, database, updates and security guidance.

## Portfolio Focus

This project demonstrates practical work with security-oriented backend development, Linux infrastructure, Docker, authentication, cryptographic integrity controls, endpoint management and DFIR-oriented tooling.
