import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_db
from .routes import items, transactions, ai

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="StokPintar UMKM — Asisten Operasional & Kasir AI",
    description="Platform manajemen stok barang dan pencatatan kas otomatis bertenaga Google Gemini AI untuk LOGICODIX 2026",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(items.router)
app.include_router(transactions.router)
app.include_router(ai.router)

# Static files & SPA root
STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", include_in_schema=False)
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "StokPintar UMKM API Active. Buka /docs untuk API Swagger."}

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "StokPintar UMKM", "competition": "LOGICODIX 2026"}
