import os
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

ZT_HOST = os.getenv("ZT_HOST", "zerotier")
ZT_PORT = int(os.getenv("ZT_PORT", "9993"))
ZT_AUTHTOKEN_PATH = Path(os.getenv("ZT_AUTHTOKEN_PATH", "/var/lib/zerotier-one/authtoken.secret"))

app = FastAPI(title="ZeroTier")
templates = Jinja2Templates(directory="app/templates")


def read_token() -> str | None:
    try:
        return ZT_AUTHTOKEN_PATH.read_text().strip()
    except FileNotFoundError:
        return None


def validate_nwid(nwid: str) -> str:
    nwid = nwid.strip().lower()
    if len(nwid) != 16 or any(c not in "0123456789abcdef" for c in nwid):
        raise HTTPException(status_code=400, detail="Network ID must be 16 hex characters")
    return nwid


async def zt_request(method: str, path: str) -> httpx.Response:
    token = read_token()
    if not token:
        raise HTTPException(status_code=503, detail="ZeroTier daemon is still starting")
    url = f"http://{ZT_HOST}:{ZT_PORT}{path}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        return await client.request(method, url, headers={"X-ZT1-Auth": token})


async def gather_status() -> dict:
    token = read_token()
    if not token:
        return {"ready": False, "status": None, "networks": []}
    try:
        status_resp, networks_resp = (
            await zt_request("GET", "/status"),
            await zt_request("GET", "/network"),
        )
    except httpx.HTTPError:
        return {"ready": False, "status": None, "networks": []}
    return {
        "ready": True,
        "status": status_resp.json(),
        "networks": networks_resp.json(),
    }


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, **(await gather_status())})


@app.get("/api/status")
async def api_status():
    return await gather_status()


@app.post("/join")
async def join(network_id: Annotated[str, Form()]):
    nwid = validate_nwid(network_id)
    resp = await zt_request("POST", f"/network/{nwid}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return RedirectResponse(url="/", status_code=303)


@app.post("/leave/{network_id}")
async def leave(network_id: str):
    nwid = validate_nwid(network_id)
    resp = await zt_request("DELETE", f"/network/{nwid}")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return RedirectResponse(url="/", status_code=303)
