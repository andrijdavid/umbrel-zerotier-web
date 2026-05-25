# umbrel-zerotier-web

Tiny FastAPI UI for joining and leaving ZeroTier networks from umbrelOS. Companion to the `zerotier` app in [andrijdavid/umbrel-apps](https://github.com/andrijdavid/umbrel-apps).

The image runs alongside the official `zerotier/zerotier` daemon, reads the daemon's local API auth token from a shared volume, and proxies the user's clicks to the daemon's JSON API.

## Topology

The ZeroTier daemon binds its control plane to `127.0.0.1:9993` only, and its `authtoken.secret` file is `0600 root:root`. To work around both constraints without modifying the upstream image:

- The web container shares the daemon container's network namespace (`network_mode: "service:zerotier"` in compose), so `127.0.0.1` resolves to the same loopback for both. Web reaches the daemon at `127.0.0.1:9993`.
- The web container runs as root so it can read the daemon's 0600 token file from the shared `:ro` volume. The image is a small ASGI proxy on a private docker network behind umbrelOS's `app_proxy` auth, so the blast radius is bounded.

A side effect of sharing the network namespace: the web container has no DNS entry of its own. The umbrelOS `app_proxy` therefore points at the daemon container's name (e.g. `zerotier_zerotier_1`) on port 8080.

## Endpoints

| Route                  | Method | Purpose                                |
| ---------------------- | ------ | -------------------------------------- |
| `/`                    | GET    | HTML page (status, networks, join)     |
| `/api/status`          | GET    | JSON status used by the page           |
| `/join`                | POST   | Form: `network_id` (16 hex chars)      |
| `/leave/{network_id}`  | POST   | Leave a network                        |

## Configuration

| Variable             | Default                                       |
| -------------------- | --------------------------------------------- |
| `ZT_HOST`            | `127.0.0.1`                                   |
| `ZT_PORT`            | `9993`                                        |
| `ZT_AUTHTOKEN_PATH`  | `/var/lib/zerotier-one/authtoken.secret`      |

## Local dev

```sh
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
sudo ZT_AUTHTOKEN_PATH=/var/lib/zerotier-one/authtoken.secret \
  uvicorn app.main:app --reload
```

Needs a real ZeroTier install on the host. `sudo` so Python can read the daemon's token.

## Releasing

1. Commit, tag `vX.Y.Z`, push the tag (no need to bump `version` in `pyproject.toml` until the API or behaviour changes meaningfully).
2. GitHub Actions lints with ruff, builds the multi-arch image, and publishes to `ghcr.io/<owner>/umbrel-zerotier-web:X.Y.Z`.
3. Grab the digest from the workflow summary and pin it in the umbrel-apps fork's `zerotier/docker-compose.yml`.

## License

AGPL-3.0-or-later. See `LICENSE`.
