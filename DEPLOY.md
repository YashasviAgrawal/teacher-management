# Production Deployment Guide

## Architecture

```
Internet → Caddy (ports 80/443) → web (internal :8000, gunicorn)
```

Caddy terminates TLS with automatic Let's Encrypt certificates and proxies
traffic to the Django container on the internal Docker network.  Port 8000 is
**not** published to the host — all external traffic must enter through Caddy.

---

## Prerequisites (manual steps — not automated)

1. **DNS** — Create an A record pointing `DOMAIN` (e.g. `api.yourdomain.com`)
   at the public IP of the EC2 instance.  Propagation can take a few minutes.

2. **EC2 Security Group** — Open inbound TCP ports **80** and **443**; close
   port **8000** (or restrict it to `0.0.0.0/0` → remove the rule entirely).

3. **Elastic IP** (recommended) — Attach an Elastic IP so the DNS record
   stays stable across instance restarts.

---

## Environment variables

Copy `.env.example` to `.env` and fill in every value:

```bash
cp .env.example .env
$EDITOR .env
```

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Long random string — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hostnames Django will accept, e.g. `api.yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins for CSRF, e.g. `https://api.yourdomain.com,https://your-frontend.vercel.app` |
| `FRONTEND_ORIGINS` | Comma-separated CORS origins, e.g. `https://your-frontend.vercel.app` |
| `DOMAIN` | The subdomain Caddy listens on, e.g. `api.yourdomain.com` |
| `LETSENCRYPT_EMAIL` | Email for Let's Encrypt certificate notifications |
| `SUPABASE_DB_*` | PostgreSQL credentials (leave blank to use SQLite) |

---

## Deploy

```bash
# Build images and start all services in the background
docker compose up -d --build

# Watch Caddy obtain the Let's Encrypt certificate (takes ~10 s on first boot)
docker compose logs -f caddy

# Watch Django / gunicorn startup
docker compose logs -f web
```

---

## Verify the fix

Once deployed and DNS has propagated:

```bash
# Expect HTTP 200 (or your API's root response) over HTTPS with a valid cert
curl -v https://api.yourdomain.com/

# Check the certificate details
curl -I https://api.yourdomain.com/

# Confirm the Django container is NOT reachable directly on port 8000
curl http://<EC2-public-IP>:8000/   # should time out / be refused
```

A successful response from the `curl -v` command will show:
- `SSL connection using TLSv1.3` (or TLSv1.2)
- A certificate issued by `R10` or `R11` (Let's Encrypt)
- `HTTP/2 200` (or the expected status for your root URL)

---

## Local development

For local HTTP development, create a `.env` with:

```
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=any-local-dev-key
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=
FRONTEND_ORIGINS=http://localhost:3000
DOMAIN=localhost
LETSENCRYPT_EMAIL=dev@localhost
```

Then run:

```bash
docker compose up
```

Django will be reachable at `http://localhost` (via Caddy, plain HTTP on port 80)
and the dev container's gunicorn is available internally on port 8000.
