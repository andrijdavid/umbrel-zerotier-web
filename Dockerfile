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
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
