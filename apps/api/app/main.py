from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, clients, devices

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.api_prefix
app.include_router(auth.router, prefix=api)
app.include_router(devices.router, prefix=api)
app.include_router(clients.router, prefix=api)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ahoy-api"}
