# Demo Runbook — M01 Foundation

Scope: infrastructure only. There are no business or AI features yet.

## 1. Start the stack

```bash
cp .env.example .env
docker compose up --build
```

Wait until all services report healthy:

```bash
docker compose ps
```

## 2. Frontend through Nginx

Open <http://localhost> — expected page:

```text
AI Finance Controller

System foundation online.
```

## 3. API health check through Nginx

```bash
curl http://localhost/api/health
```

Expected response:

```json
{
  "status": "healthy",
  "service": "finance-controller-api"
}
```

## 4. Database extensions

```bash
docker compose exec postgres psql -U finance_user -d finance_controller -c "\dx"
```

Expected: `vector` and `pgcrypto` listed among installed extensions.

## 5. Celery worker

```bash
docker compose logs worker
```

Expected log lines similar to:

```text
[config] ... broker: redis://redis:6379/0
[queues] .> exchange: celery(direct) binding: celery
[tasks]   . finance_worker...
[worker]  celery@<host> ready.
```

## 6. Teardown

```bash
docker compose down          # keep data
docker compose down -v       # remove the pgdata volume as well
```
