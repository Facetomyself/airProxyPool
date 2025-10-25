from fastapi import FastAPI
from features.proxy_pool.interface.api import router as proxy_router
from features.proxy_pool.application import services

app = FastAPI(title="airProxyPool API", version="0.1.0")

@app.on_event("startup")
def _startup():
    services.bootstrap()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

app.include_router(proxy_router, prefix="/api")
