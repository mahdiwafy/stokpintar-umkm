from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ItemCreate(BaseModel):
    barcode: Optional[str] = None
    name: str = Field(..., min_length=1, description="Nama barang dagangan")
    category: str = Field(default="Umum")
    unit: str = Field(default="pcs")
    cost_price: float = Field(default=0.0, ge=0)
    selling_price: float = Field(default=0.0, ge=0)
    current_stock: float = Field(default=0.0, ge=0)
    min_stock: float = Field(default=5.0, ge=0)

class ItemUpdate(BaseModel):
    barcode: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    min_stock: Optional[float] = None

class ItemStockAdjust(BaseModel):
    actual_stock: float = Field(..., ge=0, description="Jumlah fisik stok hasil cek lapangan")
    notes: Optional[str] = Field(default="Penyesuaian stok berkala")

class ItemResponse(BaseModel):
    id: int
    barcode: Optional[str] = None
    name: str
    category: str
    unit: str
    cost_price: float
    selling_price: float
    current_stock: float
    min_stock: float
    is_low_stock: bool
    created_at: str
    updated_at: str

class CartItem(BaseModel):
    item_id: int
    quantity: float = Field(..., gt=0)
    price_per_unit: Optional[float] = None

class SaleCreate(BaseModel):
    items: List[CartItem]
    notes: Optional[str] = None

class RestockItem(BaseModel):
    item_id: Optional[int] = None
    name: Optional[str] = None
    quantity: float = Field(..., gt=0)
    cost_price: float = Field(..., ge=0)
    selling_price: Optional[float] = None

class RestockCreate(BaseModel):
    items: List[RestockItem]
    notes: Optional[str] = None

class TransactionDetail(BaseModel):
    id: int
    type: str
    total_amount: float
    notes: Optional[str] = None
    created_at: str
    items_count: int

class AIChatPrompt(BaseModel):
    prompt: str
