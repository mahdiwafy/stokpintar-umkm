from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from ..database import get_db
from ..services.gemini import parse_receipt_image, parse_natural_sale_input, generate_stock_advice
from ..models import AIChatPrompt

router = APIRouter(prefix="/api/ai", tags=["Google Gemini AI Assistant"])

@router.post("/parse-receipt")
async def parse_receipt(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Berkas harus berupa gambar (JPG, PNG, WEBP)")
    
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran gambar maksimal 10MB")
    
    result = await parse_receipt_image(contents, mime_type=content_type, api_key=api_key)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Gagal memproses nota via Gemini AI"))
    
    return result

@router.post("/parse-sale-prompt")
async def parse_sale_prompt(
    payload: AIChatPrompt,
    api_key: Optional[str] = None
):
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, unit, selling_price, current_stock FROM items;").fetchall()
        items_list = [dict(r) for r in rows]

    result = await parse_natural_sale_input(payload.prompt, items_list, api_key=api_key)
    return result

@router.get("/stock-advice")
async def get_stock_recommendation(api_key: Optional[str] = None):
    with get_db() as conn:
        items = [dict(r) for r in conn.execute("SELECT * FROM items ORDER BY (current_stock <= min_stock) DESC;").fetchall()]
        recent_txs = [dict(r) for r in conn.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 15;").fetchall()]

    result = await generate_stock_advice(items, recent_txs, api_key=api_key)
    return result
