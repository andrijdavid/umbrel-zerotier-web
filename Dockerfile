FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

# Runs as root so it can read the ZeroTier daemon's 0600 root-owned
# authtoken.secret from the shared :ro volume. Tiny ASGI app on a private
# docker network behind app_proxy auth, so the blast radius is small.

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- --tries=1 http://127.0.0.1:8080/api/status >/dev/null || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
