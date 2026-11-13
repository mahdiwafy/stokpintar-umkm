import os
import json
import base64
import httpx
from typing import Optional, List, Dict, Any

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

def get_api_key(override_key: Optional[str] = None) -> Optional[str]:
    return override_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

async def call_gemini(
    contents: List[Dict[str, Any]],
    system_instruction: Optional[str] = None,
    api_key: Optional[str] = None,
    json_mode: bool = True
) -> Dict[str, Any]:
    key = get_api_key(api_key)
    if not key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY tidak ditemukan. Mohon setel GEMINI_API_KEY di environment atau pengaturan.",
            "data": None
        }

    url = f"{GEMINI_API_URL}?key={key}"
    payload: Dict[str, Any] = {
        "contents": contents
    }
    
    generation_config: Dict[str, Any] = {
        "temperature": 0.2,
        "maxOutputTokens": 2048,
    }
    if json_mode:
        generation_config["responseMimeType"] = "application/json"
    
    payload["generationConfig"] = generation_config

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                return {
                    "success": False,
                    "error": f"Google Gemini API Error ({resp.status_code}): {resp.text}",
                    "data": None
                }
            
            result = resp.json()
            candidates = result.get("candidates", [])
            if not candidates:
                return {"success": False, "error": "Tidak ada respon dari model Gemini.", "data": None}
            
            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if json_mode:
                try:
                    parsed = json.loads(raw_text)
                    return {"success": True, "data": parsed, "raw": raw_text}
                except json.JSONDecodeError:
                    return {"success": True, "data": raw_text, "raw": raw_text}
            
            return {"success": True, "data": raw_text}

    except Exception as e:
        return {"success": False, "error": f"Koneksi ke Google AI gagal: {str(e)}", "data": None}

async def parse_receipt_image(image_bytes: bytes, mime_type: str = "image/jpeg", api_key: Optional[str] = None) -> Dict[str, Any]:
    key = get_api_key(api_key)
    if not key:
        # Fallback simulated parse for testing without key
        return {
            "success": True,
            "simulated": True,
            "data": {
                "store_name": "Toko Grosir Rejeki (Simulasi)",
                "date": "2026-11-09",
                "total_receipt": 182000,
                "items": [
                    {"name": "Minyak Goreng 1L", "quantity": 5, "unit": "pouch", "cost_price": 15500, "subtotal": 77500},
                    {"name": "Gula Pasir 1kg", "quantity": 5, "unit": "kg", "cost_price": 14500, "subtotal": 72500},
                    {"name": "Kopi Kapal Api Sachet", "quantity": 2, "unit": "renceng", "cost_price": 11000, "subtotal": 22000},
                    {"name": "Sabun Cuci Piring 750ml", "quantity": 1, "unit": "botol", "cost_price": 10000, "subtotal": 10000}
                ]
            }
        }

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    system_instruction = (
        "Anda adalah asisten AI kasir dan akuntansi UMKM Indonesia. "
        "Tugas Anda mengekstrak isi nota/struk belanja kulakan barang warung menjadi format JSON baku. "
        "Ekstrak store_name (nama toko), date (tanggal nota format YYYY-MM-DD), total_receipt (total belanja nominal angka), "
        "dan daftar items: [name, quantity (angka float), unit (pcs/kg/pouch/karung/dsb), cost_price (harga beli satuan angka), subtotal (angka)]."
    )

    contents = [{
        "parts": [
            {"text": "Tolong baca nota/struk belanja ini dan ekstrak seluruh barang yang dibeli beserta harga kulakannya ke JSON."},
            {
                "inlineData": {
                    "mimeType": mime_type,
                    "data": b64_image
                }
            }
        ]
    }]

    return await call_gemini(contents, system_instruction=system_instruction, api_key=key, json_mode=True)

async def parse_natural_sale_input(text_prompt: str, existing_items: List[Dict[str, Any]], api_key: Optional[str] = None) -> Dict[str, Any]:
    key = get_api_key(api_key)
    if not key:
        # Simple keyword matching fallback
        matched = []
        lower = text_prompt.lower()
        for item in existing_items:
            if item["name"].lower() in lower:
                matched.append({
                    "item_id": item["id"],
                    "item_name": item["name"],
                    "quantity": 1.0,
                    "selling_price": item["selling_price"]
                })
        return {
            "success": True,
            "simulated": True,
            "data": {
                "recognized_items": matched,
                "notes": f"Pencatatan suara/teks: {text_prompt}"
            }
        }

    items_catalog = [
        {"id": it["id"], "name": it["name"], "unit": it["unit"], "selling_price": it["selling_price"], "stock": it["current_stock"]}
        for it in existing_items
    ]

    system_instruction = (
        "Anda adalah asisten kasir cerdas warung UMKM. "
        "Pengguna akan mendiktekan atau mengetikkan transaksi penjualan secara santai dalam Bahasa Indonesia. "
        "Tugas Anda mencocokkan barang yang disebutkan dengan katalog barang yang tersedia, dan menentukan jumlah kuantitasnya. "
        "Katalog yang tersedia: " + json.dumps(items_catalog, ensure_ascii=False) + ". "
        "Kembalikan JSON dengan format: "
        "{ 'recognized_items': [ { 'item_id': int, 'item_name': str, 'quantity': float, 'selling_price': float } ], 'unmatched_text': str, 'notes': str }"
    )

    contents = [{
        "parts": [{"text": text_prompt}]
    }]

    return await call_gemini(contents, system_instruction=system_instruction, api_key=key, json_mode=True)

async def generate_stock_advice(items_list: List[Dict[str, Any]], recent_transactions: List[Dict[str, Any]], api_key: Optional[str] = None) -> Dict[str, Any]:
    key = get_api_key(api_key)
    critical_items = [it for it in items_list if it["current_stock"] <= it["min_stock"]]

    if not key:
        advice_list = []
        for it in critical_items:
            advice_list.append(f"Stok {it['name']} tersisa {it['current_stock']} {it['unit']} (batas minimum: {it['min_stock']}). Disarankan kulakan minimal {it['min_stock'] * 2} {it['unit']}.")
        
        return {
            "success": True,
            "simulated": True,
            "data": {
                "summary": f"Ditemukan {len(critical_items)} barang dengan stok kritis.",
                "action_items": advice_list,
                "estimated_budget": sum(it["cost_price"] * (it["min_stock"] * 2) for it in critical_items)
            }
        }

    system_instruction = (
        "Anda adalah konsultan operasional & rantai pasok UMKM berpengalaman. "
        "Analisis data inventaris barang toko dan berikan rekomendasi aksi belanja/kulakan yang cerdas, hemat kas, "
        "dan mencegah kehabisan stok saat pelanggan datang. "
        "Format JSON: { 'summary': str, 'urgent_restock': [ { 'item_name': str, 'current_stock': float, 'suggested_buy_qty': float, 'reason': str } ], 'estimated_budget': float, 'operational_tips': [str] }"
    )

    data_payload = {
        "inventory": items_list,
        "recent_sales_snippet": recent_transactions[:10]
    }

    contents = [{
        "parts": [{"text": f"Berikut adalah data stok barang kami saat ini: {json.dumps(data_payload, ensure_ascii=False)}. Berikan rekomendasi stok belanja."}]
    }]

    return await call_gemini(contents, system_instruction=system_instruction, api_key=key, json_mode=True)
