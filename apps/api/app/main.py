from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import auth, brand, campaigns, clients, devices, marketing, media, queue, reviews, roi

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.3.0")

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
app.include_router(brand.router, prefix=api)
app.include_router(media.router, prefix=api)
app.include_router(campaigns.router, prefix=api)
app.include_router(queue.router, prefix=api)
app.include_router(roi.router, prefix=api)
app.include_router(reviews.router, prefix=api)
app.include_router(marketing.router, prefix=api)

upload_root = Path(settings.upload_dir)
if not upload_root.is_absolute():
    upload_root = Path.cwd() / upload_root
upload_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_root)), name="uploads")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ahoy-api"}
