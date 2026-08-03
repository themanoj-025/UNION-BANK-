# Union Bank Management System — Docker Guide

## Quick start

```bash
cp .env.example .env   # set real POSTGRES_PASSWORD etc.
docker compose up -d
```

Starts FastAPI (`:8000`), PostgreSQL (`:5432`), and Redis (`:6379`,
internal-only in prod). The Dockerfile is multi-stage: `base` → `api`
(production) and `base` → `dev` (hot reload).

## Image targets

```bash
docker build --target api -t union-bank/api .   # production
docker compose -f docker-compose.yml -f docker-compose.dev.yml up   # dev
```

## Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Hardens: hides Postgres/Redis host ports, adds CPU/memory limits, and
adds Prometheus (`:9090`) + Grafana (`:3000`) observability.

## Environment

Key vars: `DATABASE_URL`, `REDIS_URL`, `UNION_BANK_TESTING`, `ENV`,
`UVICORN_WORKERS` (see `.env.example`).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| API crash-loops | Postgres must be healthy first; check `docker compose logs api` |
| Grafana admin creds | Defaults `admin`/`admin` — change in prod override |
| Port conflicts | Adjust `ports` per service |
