# umbrel-zerotier-web

Tiny FastAPI UI for joining and leaving ZeroTier networks from umbrelOS. Companion to the `zerotier` app in [andrijdavid/umbrel-apps](https://github.com/andrijdavid/umbrel-apps).

Runs alongside the official `zerotier/zerotier` daemon, reads the daemon's local API auth token from a shared volume, and proxies the user's clicks to the daemon's JSON API at `http://$ZT_HOST:$ZT_PORT`.

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
| `ZT_HOST`            | `zerotier`                                    |
| `ZT_PORT`            | `9993`                                        |
| `ZT_AUTHTOKEN_PATH`  | `/var/lib/zerotier-one/authtoken.secret`      |

## Local dev

```sh
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
ZT_HOST=localhost ZT_AUTHTOKEN_PATH=/var/lib/zerotier-one/authtoken.secret \
  uvicorn app.main:app --reload
```

Needs a real ZeroTier install on the host and read access to its `authtoken.secret`.

## Releasing

1. Bump `version` in `pyproject.toml`.
2. Commit, tag `vX.Y.Z`, push the tag.
3. GitHub Actions builds the multi-arch image and publishes to `ghcr.io/<owner>/umbrel-zerotier-web:X.Y.Z`.
4. Grab the digest from the workflow summary, paste it into the umbrel-apps fork's `zerotier/docker-compose.yml`, and bump the `zerotier/web` submodule pin to this commit.

## License

AGPL-3.0-or-later. See `LICENSE`.
