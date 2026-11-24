"""EcoRoute FastAPI uygulaması.

Çalıştırma (proje kök klasöründen):
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Pano:     http://127.0.0.1:8000/
Swagger:  http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .database import Base, SessionLocal, engine
from .routers import routes
from .seed import seed

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)  # tablolar boşsa örnek veriyi yükler
    yield


app = FastAPI(
    title="EcoRoute API",
    version="0.1.0",
    description=(
        "Belediyeler için akıllı atık toplama ve dinamik rota optimizasyonu. "
        "Yalnızca doluluğu %80 ve üzeri olan (veya kritik alarm veren) konteynerleri hedefleyen, "
        "yakıt ve mesafe tasarrufu sağlayan rotalar üretir."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Konteynerler", "description": "Akıllı konteyner ve sensör verileri"},
        {"name": "Araçlar", "description": "Atık toplama filosu"},
        {"name": "Rota Optimizasyonu", "description": "Eşik filtresi + En Yakın Komşu + 2-opt"},
        {"name": "Analitik", "description": "KPI, trend ve karar destek önerileri"},
        {"name": "IoT Simülasyonu", "description": "Geliştirme / demo amaçlı simülasyon uçları"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # üretimde belediye panosunun alan adıyla sınırlandırın
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND)


@app.get("/health", tags=["Sistem"], summary="Sağlık kontrolü")
def health():
    return {"status": "ok"}
