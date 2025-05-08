from collections import defaultdict
import simpy
from datetime import date, timedelta
from models import Product, InventoryItem, Supplier, BOMItem, Order, PurchaseOrder, Event
import random

class Simulator:
    def __init__(self, env, daily_capacity=10):
        self.env = env
        self.day = 1
        self.daily_capacity = daily_capacity
        self.inventory = {}  # {product_id: qty}
        self.orders = []
        self.purchase_orders = []
        self.events = []
        self.suppliers = []
        self.boms = []
        self.products = []
        self.current_date = date.today()
        self.inventory_history = []
        self.production_log = []

    def log_event(self, event_type, detail):
        event = Event(
            id=len(self.events) + 1,
            event_type=event_type,
            sim_date=self.current_date,
            detail=detail
        )
        self.events.append(event)

    def advance_day(self, media=5, desviacion=2):
        self.day += 1
        self.current_date += timedelta(days=1)
        self.run_day()
        self.env.run(until=self.env.now + 1)
        self.inventory_history.append({k: v for k, v in self.inventory.items()})
        self.generar_pedidos(media, desviacion)

    def run_day(self):
        self.process_purchases()
        self.process_production()
        self.log_event("stock", f"Día {self.day} procesado.")

    def process_purchases(self):
        for po in self.purchase_orders:
            if po.status == "ordered" and po.expected_arrival <= self.current_date:
                self.inventory[po.product_id] = self.inventory.get(po.product_id, 0) + po.quantity
                po.status = "received"
                self.log_event("purchase", f"Llegaron {po.quantity} unidades del producto {po.product_id}.")

    def process_production(self):
        capacity = self.daily_capacity
        produccion_por_producto = defaultdict(int)
        for order in self.orders:
            if order.status == "released" and capacity > 0:
                required = self.get_bom_for_product(order.product_id)
                if self.can_produce(required, order.quantity):
                    self.consume_materials(required, order.quantity)
                    self.inventory[order.product_id] = self.inventory.get(order.product_id, 0) + order.quantity
                    order.status = "completed"
                    capacity -= order.quantity
                    produccion_por_producto[order.product_id] += order.quantity
                    self.log_event("production", f"Se produjeron {order.quantity} unidades del producto {order.product_id}.")
        
        self.production_log.append({
                    "date": self.current_date,
                    "produced": dict(produccion_por_producto)
        })    

    def get_bom_for_product(self, product_id):
        return [b for b in self.boms if b.finished_product_id == product_id]

    def can_produce(self, bom_items, quantity):
        for item in bom_items:
            if self.inventory.get(item.material_id, 0) < item.quantity * quantity:
                return False
        return True

    def consume_materials(self, bom_items, quantity):
        for item in bom_items:
            self.inventory[item.material_id] -= item.quantity * quantity

    def generar_pedidos(self, media=5, desviacion=2):
        # Filtrar productos que son de tipo "finished"
        productos_finales = [p for p in self.products if p.type == "finished"]
        if not productos_finales:
            return  # Nada que generar

        cantidad = max(1, int(random.gauss(media, desviacion)))
        producto = random.choice(productos_finales)

        nuevo = Order(
            id=len(self.orders) + 1,
            creation_date=self.current_date,
            product_id=producto.id,
            quantity=cantidad,
            status="pending"
        )
        self.orders.append(nuevo)
        self.log_event("order", f"Pedido automático generado: {cantidad} unidades del producto {producto.name}.")
