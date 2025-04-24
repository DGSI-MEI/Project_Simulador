from pydantic import BaseModel, Field
from typing import Literal, Dict, List, Optional
from datetime import datetime

class Product(BaseModel):
    id: int
    name: str
    type: Literal["raw", "finished"]
    description: Optional[str] = None

class BOM(BaseModel):
    prod_terminado_id: int
    material_id: int
    quantity: int

class Supplier(BaseModel):
    id: int
    name: str
    product_id: int
    unit_cost: float
    lead_time: int  # días
    min_order_quantity: Optional[int] = None
    max_order_quantity: Optional[int] = None

class InventoryItem(BaseModel):
    product_id: int
    qty: int
    min_stock: Optional[int] = Field(default=0)
    max_stock: Optional[int] = Field(default=1000)

class ProductionOrder(BaseModel):
    id: int
    creation_date: datetime
    product_id: int
    quantity: int
    status: Literal["pending", "in_progress", "completed", "cancelled"]
    estimated_completion_date: Optional[datetime] = None

class PurchaseOrder(BaseModel):
    id: int
    supplier_id: int
    product_id: int
    quantity: int
    emission_date: datetime
    estimated_delivery_date: datetime
    status: Literal["pending", "in_transit", "delivered", "cancelled"]
    unit_price: float

class Event(BaseModel):
    id: int
    type: Literal["production", "purchase", "inventory", "demand"]
    simulation_date: datetime
    details: Dict
    
class ProductionPlan(BaseModel):
    capacity_per_day: int
    models: Dict[str, Dict[str, Dict[str, int]]]
    plan: List[Dict]

class SimulationConfig(BaseModel):
    demand_mean: float
    demand_variance: float
    initial_stock: Dict[int, int]  # product_id: quantity
    warehouse_capacity: int
    simulation_days: int

class DailyStats(BaseModel):
    day: int
    total_production: int
    total_orders: int
    inventory_levels: Dict[int, int]  # product_id: quantity
    pending_orders: int
    completed_orders: int