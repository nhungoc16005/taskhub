from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.error_handlers import register_exception_handlers

app = FastAPI(title="TaskHub")
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
