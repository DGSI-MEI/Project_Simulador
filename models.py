from pydantic import BaseModel
from typing import Literal, List, Optional
from datetime import date

class Product(BaseModel):
    id: int
    name: str
    type: Literal["raw", "finished"]

class InventoryItem(BaseModel):
    product_id: int
    qty: int

class Supplier(BaseModel):
    id: int
    name: str
    product_id: int
    unit_cost: float
    lead_time: int  # en días

class BOMItem(BaseModel):
    finished_product_id: int
    material_id: int
    quantity: int

class Order(BaseModel):
    id: int
    creation_date: date
    product_id: int
    quantity: int
    status: Literal["pending","released", "in_production", "completed"]
    delivery_date: Optional[date] = None  # ✅ nuevo campo
    initial_quantity: Optional[int] = None


class PurchaseOrder(BaseModel):
    id: int
    supplier_id: int
    product_id: int
    quantity: int
    order_date: date
    expected_arrival: date
    status: Literal["ordered", "received"]

class Event(BaseModel):
    id: int
    sim_date: date
    type: Literal["purchase", "stock", "order", "production"]
    description: str

    # Campos comunes opcionales
    product_id: Optional[int] = None           # Material o producto terminado
    order_id: Optional[int] = None             # ID de pedido de cliente
    supplier_id: Optional[int] = None          # ID del proveedor si aplica
    quantity: Optional[int] = None             # Cuántas unidades se ven afectadas

    # Extra para información adicional (nombres, motivos, etc.)
    extra: Optional[dict] = None

