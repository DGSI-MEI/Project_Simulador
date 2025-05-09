from collections import defaultdict
from typing import Literal, Optional
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

    def log_event(
    self,
    event_type: Literal["purchase", "stock", "order", "production"],
    description: str,
    product_id: Optional[int] = None,
    order_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    quantity: Optional[int] = None,
    extra: Optional[dict] = None
    ):
        event = Event(
            id=len(self.events) + 1,
            sim_date=self.current_date,
            type=event_type,
            description=description,
            product_id=product_id,
            order_id=order_id,
            supplier_id=supplier_id,
            quantity=quantity,
            extra=extra
        )
        self.events.append(event)


    def advance_day(self, media=5, desviacion=2,tiempo_base_entrega=3):
        self.day += 1
        self.current_date += timedelta(days=1)
        self.run_day()
        self.env.run(until=self.env.now + 1)
        self.inventory_history.append({
            "date": self.current_date,
            "inventory": self.inventory.copy()
        })
        self.generar_pedidos(media, desviacion,tiempo_base_entrega)
       

    def run_day(self):
        self.process_purchases()
        self.process_production()
        self.log_event(
            event_type="stock",
            description="Día procesado",
            extra={"day": self.day}
        )

    def process_purchases(self):
        for po in self.purchase_orders:
            if po.status == "ordered" and po.expected_arrival <= self.current_date:
                self.inventory[po.product_id] = self.inventory.get(po.product_id, 0) + po.quantity
                po.status = "received"
                self.log_event(
                    event_type="purchase",
                    description="Recepción de orden de compra",
                    product_id=po.product_id,
                    supplier_id=po.supplier_id,
                    quantity=po.quantity,
                    extra={
                        "purchase_order_id": po.id,
                        "expected_arrival": po.expected_arrival.isoformat()
                    }
                )

    def process_production(self):
        capacity = self.daily_capacity
        produccion_por_producto = defaultdict(int)

        for order in self.orders:
            if order.status == "released" and capacity > 0:
                required = self.get_bom_for_product(order.product_id)

                # Determinar el máximo que se puede producir hoy
                max_producible = min(capacity, self.max_units_producible(required))
                if max_producible == 0:
                    continue

                cantidad_producida = min(order.quantity, max_producible)

                # Consumir materiales y actualizar inventario
                self.consume_materials(required, cantidad_producida)
                self.inventory[order.product_id] = self.inventory.get(order.product_id, 0) + cantidad_producida
                order.quantity -= cantidad_producida
                capacity -= cantidad_producida
                produccion_por_producto[order.product_id] += cantidad_producida

                # Log de producción parcial
                self.log_event(
                    event_type="production",
                    description="Producción parcial realizada",
                    product_id=order.product_id,
                    order_id=order.id,
                    quantity=cantidad_producida,
                    extra={
                        "pedido_restante": order.quantity,
                        "capacidad_restante": capacity
                    }
                )

                # Si el pedido se completa
                if order.quantity == 0:
                    order.status = "completed"
                    self.log_event(
                        event_type="production",
                        description="Pedido completado en producción",
                        product_id=order.product_id,
                        order_id=order.id,
                        quantity=0,
                        extra={"estado": "completado"}
                    )

        self.production_log.append({
            "date": self.current_date,
            "produced": dict(produccion_por_producto)
        })
        
    def max_units_producible(self, bom_items):
        unidades_posibles = []
        for item in bom_items:
            disponibles = self.inventory.get(item.material_id, 0)
            if item.quantity == 0:
                continue
            unidades = disponibles // item.quantity
            unidades_posibles.append(unidades)
        return min(unidades_posibles) if unidades_posibles else 0

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

    def generar_pedidos(self, media=5, desviacion=2, tiempo_base_entrega=3):
        # Filtrar productos que son de tipo "finished"
        productos_finales = [p for p in self.products if p.type == "finished"]
        if not productos_finales:
            return  # Nada que generar

        cantidad = max(1, int(random.gauss(media, desviacion)))
        producto = random.choice(productos_finales)

        dias_base = tiempo_base_entrega  # tiempo mínimo
        dias_extra = cantidad // 5  # +1 día por cada 5 unidades
        entrega_estim = self.current_date + timedelta(days=dias_base + dias_extra)

        nuevo = Order(
            id=len(self.orders) + 1,
            creation_date=self.current_date,
            product_id=producto.id,
            quantity=cantidad,
            status="pending",
            delivery_date=entrega_estim,
            initial_quantity=cantidad
        )
        self.orders.append(nuevo)

        self.log_event(
            event_type="order",
            description="Pedido automático generado",
            product_id=producto.id,
            quantity=cantidad,
            order_id=nuevo.id,
            extra={
                "product_name": producto.name,
                "delivery_date": entrega_estim.isoformat(),
                "tiempo_base": dias_base,
                "dias_extra": dias_extra,
                "dias_totales": dias_base + dias_extra
            }
        )
