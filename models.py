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
    event_type: Literal["production", "purchase", "stock", "order"]
    sim_date: date
    detail: str
