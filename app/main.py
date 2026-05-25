import os
from pathlib import Path
from typing import Annotated
from urllib.parse import quote_plus

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ZT_HOST = os.getenv("ZT_HOST", "127.0.0.1")
ZT_PORT = int(os.getenv("ZT_PORT", "9993"))
ZT_AUTHTOKEN_PATH = Path(os.getenv("ZT_AUTHTOKEN_PATH", "/var/lib/zerotier-one/authtoken.secret"))

app = FastAPI(title="ZeroTier")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


def read_token() -> tuple[str | None, str | None]:
    try:
        return ZT_AUTHTOKEN_PATH.read_text().strip(), None
    except FileNotFoundError:
        return (
            None,
            f"Auth token not found at {ZT_AUTHTOKEN_PATH}. ZeroTier daemon may still be starting.",
        )
    except PermissionError:
        return None, (
            f"Permission denied reading {ZT_AUTHTOKEN_PATH}. "
            "The web container needs to run as root so it can read the daemon's 0600 token file."
        )
    except OSError as e:
        return None, f"Cannot read {ZT_AUTHTOKEN_PATH}: {e}"


def validate_nwid(nwid: str) -> tuple[str | None, str | None]:
    nwid = nwid.strip().lower()
    if len(nwid) != 16 or any(c not in "0123456789abcdef" for c in nwid):
        return None, "Network ID must be exactly 16 hexadecimal characters."
    return nwid, None


async def zt_call(method: str, path: str) -> tuple[httpx.Response | None, str | None]:
    token, err = read_token()
    if err:
        return None, err
    url = f"http://{ZT_HOST}:{ZT_PORT}{path}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.request(method, url, headers={"X-ZT1-Auth": token})
    except httpx.ConnectError:
        return None, (
            f"Cannot reach ZeroTier daemon at {ZT_HOST}:{ZT_PORT}. "
            "The daemon binds its control plane to 127.0.0.1 only, so this container "
            "must share the daemon's network namespace (network_mode: service:zerotier)."
        )
    except httpx.HTTPError as e:
        return None, f"HTTP error talking to daemon: {e}"
    if resp.status_code == 401:
        return None, "Daemon rejected the auth token (401). Token may be stale."
    return resp, None


async def gather_status() -> dict:
    status_resp, err = await zt_call("GET", "/status")
    if err:
        return {"ready": False, "error": err, "status": None, "networks": []}
    networks_resp, err = await zt_call("GET", "/network")
    if err:
        return {"ready": False, "error": err, "status": None, "networks": []}
    if status_resp.status_code != 200 or networks_resp.status_code != 200:
        return {
            "ready": False,
            "error": f"Daemon returned {status_resp.status_code} / {networks_resp.status_code}.",
            "status": None,
            "networks": [],
        }
    return {
        "ready": True,
        "error": None,
        "status": status_resp.json(),
        "networks": networks_resp.json(),
    }


def flash(kind: str, msg: str) -> RedirectResponse:
    return RedirectResponse(url=f"/?{kind}={quote_plus(msg)}", status_code=303)


@app.get("/")
async def index(request: Request, error: str | None = None, notice: str | None = None):
    data = await gather_status()
    if error and not data.get("error"):
        data["error"] = error
    data["notice"] = notice
    return templates.TemplateResponse("index.html", {"request": request, **data})


@app.get("/api/status")
async def api_status():
    return await gather_status()


@app.post("/join")
async def join(network_id: Annotated[str, Form()]):
    nwid, err = validate_nwid(network_id)
    if err:
        return flash("error", err)
    resp, err = await zt_call("POST", f"/network/{nwid}")
    if err:
        return flash("error", err)
    if resp.status_code >= 400:
        return flash("error", f"Join failed ({resp.status_code}): {resp.text[:200]}")
    return flash("notice", f"Joined network {nwid}. Authorise this node from your controller.")


@app.post("/leave/{network_id}")
async def leave(network_id: str):
    nwid, err = validate_nwid(network_id)
    if err:
        return flash("error", err)
    resp, err = await zt_call("DELETE", f"/network/{nwid}")
    if err:
        return flash("error", err)
    if resp.status_code >= 400:
        return flash("error", f"Leave failed ({resp.status_code}): {resp.text[:200]}")
    return flash("notice", f"Left network {nwid}.")
