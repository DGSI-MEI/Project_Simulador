import streamlit as st
from simulator import Simulator
from models import Product, InventoryItem, Order, BOMItem, Supplier, PurchaseOrder, Event
import simpy
from datetime import date, timedelta, datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import json
import os
from utils.loader import cargar_configuracion

# ===== Persistencia =====
ESTADO_FILE = "./data/estado.json"
def guardar_estado(sim):
    estado = {
        "day": sim.day,
        "current_date": sim.current_date.isoformat(),
        "inventory": sim.inventory,
        "orders": [o.dict() | {"creation_date": o.creation_date.isoformat()} for o in sim.orders],
        "purchase_orders": [
            po.dict() | {
                "order_date": po.order_date.isoformat(),
                "expected_arrival": po.expected_arrival.isoformat()
            } for po in sim.purchase_orders
        ],
        "events": [e.dict() | {"sim_date": e.sim_date.isoformat()} for e in sim.events],
        "inventory_history": sim.inventory_history,
        "production_log": [
            {
                "date": log["date"].isoformat(),
                "produced": log["produced"]
            } for log in sim.production_log
        ]
    }
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)

def cargar_estado(sim):
    if os.path.exists(ESTADO_FILE) and os.path.getsize(ESTADO_FILE) > 0:
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                estado = json.load(f)
            sim.day = estado["day"]
            sim.current_date = datetime.fromisoformat(estado["current_date"]).date()
            sim.inventory = {int(k): v for k, v in estado["inventory"].items()}
            sim.orders = [Order(**{**o, "creation_date": datetime.fromisoformat(o["creation_date"]).date()}) for o in estado["orders"]]
            sim.purchase_orders = [
                PurchaseOrder(**{
                    **po,
                    "order_date": datetime.fromisoformat(po["order_date"]).date(),
                    "expected_arrival": datetime.fromisoformat(po["expected_arrival"]).date()
                }) for po in estado["purchase_orders"]
            ]
            sim.events = [Event(**{**e, "sim_date": datetime.fromisoformat(e["sim_date"]).date()}) for e in estado["events"]]
            sim.inventory_history = estado.get("inventory_history", [])
            sim.production_log = [
                {
                    "date": datetime.fromisoformat(log["date"]).date(),
                    "produced": log.get("produced", {})
                } for log in estado.get("production_log", [])
            ]
        except json.JSONDecodeError:
            st.warning("El archivo estado.json está vacío o corrupto. Se cargará un estado inicial.")

# ===== Simulación inicial =====
env = simpy.Environment()
sim = Simulator(env)    

# 1. Cargar configuración
products, boms, suppliers = cargar_configuracion()
sim.products = products
sim.boms = boms
sim.suppliers = suppliers

# 2. Si no existe estado, lo inicializamos y guardamos
if not os.path.exists(ESTADO_FILE) or os.path.getsize(ESTADO_FILE) == 0:
    import random
    sim.day = 1
    sim.current_date = date.today()

    # Crear inventario inicial de materias primas (tipo "raw") con valores entre 1 y 20
    sim.inventory = {
        product.id: random.randint(5, 20)
        for product in sim.products
        if product.type == "raw"
    }

    # Obtener IDs de productos terminados
    productos_finales = [p.id for p in sim.products if p.type == "finished"]

    # Crear dos órdenes iniciales con productos y cantidades aleatorias
    sim.orders = [
        Order(
            id=i + 1,
            creation_date=sim.current_date,
            product_id=random.choice(productos_finales),
            quantity=random.randint(1, 10),
            status="pending"
        ) for i in range(2)
    ]

    guardar_estado(sim)


# 3. Cargar estado una única vez, después de posible inicialización
cargar_estado(sim)

# ===== Lógica MRP =====
def calcular_faltantes():
    requerimientos = defaultdict(int)
    for order in sim.orders:
        if order.status in ("pending", "released"):
            for bom in sim.boms:
                if bom.finished_product_id == order.product_id:
                    requerimientos[bom.material_id] += bom.quantity * order.quantity

    faltantes = {}
    for pid, req_qty in requerimientos.items():
        en_stock = sim.inventory.get(pid, 0)
        if req_qty > en_stock:
            faltantes[pid] = req_qty - en_stock
    return faltantes


def calcular_faltantes_by_order(order):
    requerimientos = defaultdict(int)
    if order.status in ("pending", "released"):
        for bom in sim.boms:
            if bom.finished_product_id == order.product_id:
                requerimientos[bom.material_id] += bom.quantity * order.quantity

    faltantes = {}
    for pid, req_qty in requerimientos.items():
        en_stock = sim.inventory.get(pid, 0)
        if req_qty > en_stock:
            faltantes[pid] = req_qty - en_stock
    return faltantes


# ===== Encabezado =====
st.title("Simulador MRP - Producción Impresoras 3D")
st.subheader(f"Día simulado: {sim.day} ({sim.current_date})")

st.markdown("## Parámetros para creación automática de pedidos")
media = st.slider("Media de pedidos diarios", 1, 20, 5)
desviacion = st.slider("Desviación estándar de cantidad", 1, 10, 2)


if st.button("Avanzar Día"):
    st.text(f"[DEBUG 5] Día antes de avanzar: {sim.day}")
    sim.advance_day(media=media, desviacion=desviacion)
    guardar_estado(sim)
    st.text(f"[DEBUG 6] Día después de avanzar: {sim.day}")
    st.success("Día avanzado y estado guardado")
    st.rerun()


# ===== Panel Pedidos =====
st.markdown("## Pedidos Pendientes")
for order in sim.orders:
    if order.status == "pending":
        col1, col2, col3 = st.columns([3, 2, 3])
        with col1:
            product = next((p for p in sim.products if p.id == order.product_id), None)
            product_name = product.name if product else "Desconocido"
            st.write(f"Pedido #{order.id} - Producto {product_name} - Cantidad: {order.quantity}")
        with col2:
            if st.button(f"Ver/Ocultar detalle #{order.id}", key=f"toggle_{order.id}"):
                if f"detalle_visible_{order.id}" not in st.session_state:
                    st.session_state[f"detalle_visible_{order.id}"] = False
                    st.session_state[f"detalle_visible_{order.id}"] = False
                    st.session_state[f"detalle_visible_{order.id}"] = False
                st.session_state[f"detalle_visible_{order.id}"] = not st.session_state[f"detalle_visible_{order.id}"]

        if st.session_state.get(f"detalle_visible_{order.id}", False):
            st.markdown("### Materiales requeridos por pedido (BOM)")
            st.markdown(f"**Pedido #{order.id} - Producto {order.product_id} - Cantidad: {order.quantity}**")
            materiales = [b for b in sim.boms if b.finished_product_id == order.product_id]
            for mat in materiales:
                total_necesario = mat.quantity * order.quantity
                st.write(f"- Material {mat.material_id}: {mat.quantity} por unidad → Total requerido: {total_necesario}")
        
        with col3:
            if faltantes := calcular_faltantes_by_order(order):
                for pid, qty in faltantes.items():
                    st.write(f"Material {pid}: faltan {qty} unidades")
                    if st.button(f"Comprar materiales faltantes", key=f"comprar_{order.id}_{pid}"):
                        st.markdown("## Emitir Orden de Compra")
                        producto_seleccionado = pid
                        proveedores_disponibles = [s for s in sim.suppliers if s.product_id == producto_seleccionado]
                        nombres_proveedores = [f"{s.id} - {s.name} (Lead Time: {s.lead_time} días)" for s in proveedores_disponibles]
                        proveedor_elegido_idx = st.selectbox("Proveedor", list(range(len(nombres_proveedores))), format_func=lambda i: nombres_proveedores[i], key=f"proveedor_{order.id}_{pid}")
                        cantidad = st.number_input("Cantidad a comprar", min_value=qty, step=1, value=qty, key=f"cantidad_{order.id}_{pid}")

                        if st.button("Emitir Orden", key=f"emitir_{order.id}_{pid}"):
                            proveedor = proveedores_disponibles[proveedor_elegido_idx]
                            fecha_entrega = sim.current_date + timedelta(days=proveedor.lead_time)
                            nueva_oc = PurchaseOrder(
                                id=len(sim.purchase_orders) + 1,
                                supplier_id=proveedor.id,
                                product_id=proveedor.product_id,
                                quantity=cantidad,
                                order_date=sim.current_date,
                                expected_arrival=fecha_entrega,
                                status="ordered"
                            )
                            sim.purchase_orders.append(nueva_oc)
                            sim.log_event("purchase", f"Orden de compra creada: {cantidad} unidades del producto {proveedor.product_id} al proveedor {proveedor.name}.")
                            guardar_estado(sim)
                            st.success("Orden de compra emitida")
                            st.rerun()
            else:
                if st.button(f"Liberar pedido #{order.id}"):
                    order.status = "released"
                    sim.log_event("stock", f"Pedido #{order.id} liberado para producción.")
                    guardar_estado(sim)
                    st.rerun()

# ===== Panel Inventario =====
st.markdown("## Inventario")
st.markdown("### Materiales")
for pid, qty in sim.inventory.items():
    product = next((p for p in sim.products if p.id == pid and p.type == "raw"), None)
    if product:
        st.write(f"{product.name} (ID {pid}): {qty} unidades")


st.markdown("### Producto terminado")
for pid, qty in sim.inventory.items():
    product = next((p for p in sim.products if p.id == pid and p.type == "finished"), None)
    if product:
        st.write(f"Producto terminado {product.name} (ID {pid}): {qty} unidades en almacén")


st.markdown("### Debug: Órdenes y estado")
for order in sim.orders:
    st.text(f"[DEBUG] Pedido {order.id} - Estado: {order.status} - Cantidad: {order.quantity}")

st.markdown("### Debug: Inventario actual")
for pid, qty in sim.inventory.items():
    st.text(f"[DEBUG] Producto {pid} -> Stock: {qty}")

faltantes = calcular_faltantes()
if faltantes:
    st.markdown("### Faltantes detectados:")
    for pid, qty in faltantes.items():
        st.write(f"Material {pid}: faltan {qty} unidades")
else:
    st.info("No hay faltantes para los pedidos actuales.")

# ===== Panel Compras =====
st.markdown("## Emitir Orden de Compra")
producto_ids = list(set(s.product_id for s in sim.suppliers))
producto_seleccionado = st.selectbox("Producto", producto_ids)
proveedores_disponibles = [s for s in sim.suppliers if s.product_id == producto_seleccionado]
nombres_proveedores = [f"{s.id} - {s.name} (Lead Time: {s.lead_time} días)" for s in proveedores_disponibles]
proveedor_elegido_idx = st.selectbox("Proveedor", list(range(len(nombres_proveedores))), format_func=lambda i: nombres_proveedores[i])
cantidad = st.number_input("Cantidad a comprar", min_value=1, step=1)

if st.button("Emitir Orden"):
    proveedor = proveedores_disponibles[proveedor_elegido_idx]
    fecha_entrega = sim.current_date + timedelta(days=proveedor.lead_time)
    nueva_oc = PurchaseOrder(
        id=len(sim.purchase_orders) + 1,
        supplier_id=proveedor.id,
        product_id=proveedor.product_id,
        quantity=cantidad,
        order_date=sim.current_date,
        expected_arrival=fecha_entrega,
        status="ordered"
    )
    sim.purchase_orders.append(nueva_oc)
    sim.log_event("purchase", f"Orden de compra creada: {cantidad} unidades del producto {proveedor.product_id} al proveedor {proveedor.name}.")
    guardar_estado(sim)
    st.success("Orden de compra emitida")
# ===== Órdenes de Compra Emitidas =====
st.markdown("## Órdenes de Compra Emitidas")

if sim.purchase_orders:
    for po in sim.purchase_orders:
        proveedor = next((s.name for s in sim.suppliers if s.id == po.supplier_id), "Desconocido")
        st.write(f"OC #{po.id} - Producto {po.product_id} - Proveedor: {proveedor}")
        st.write(f"Cantidad: {po.quantity} | Ordenado: {po.order_date} | Llega: {po.expected_arrival} | Estado: {po.status}")
        st.markdown("---")
else:
    st.info("No hay órdenes de compra registradas.")
# ===== Panel Producción =====
st.markdown("## Producción")
st.write(f"Capacidad diaria: {sim.daily_capacity} unidades")
liberados = [o for o in sim.orders if o.status == "released"]
if liberados:
    st.markdown("### Pedidos en cola para producción:")
    for order in liberados:
        st.write(f"Pedido #{order.id} - Producto {order.product_id} - Cantidad: {order.quantity}")
else:
    st.info("No hay pedidos liberados actualmente.")

# ===== Gráficas =====
if sim.inventory_history:
    st.markdown("## Gráfica de Stock por Producto")
    for pid in sim.inventory_history[0].keys():
        valores = [dia.get(pid, 0) for dia in sim.inventory_history]
        plt.figure()
        plt.plot(range(1, len(valores)+1), valores, marker = 'o')
        plt.title(f"Stock diario - Producto {pid}")
        plt.xlabel("Día")
        plt.ylabel("Unidades")
        st.pyplot(plt)

# if sim.production_log:
#     st.markdown("## Producción diaria")
#     fechas = [log['date'] for log in sim.production_log]
#     cantidades = [log['completed_orders'] for log in sim.production_log]
#     plt.figure()
#     plt.plot(fechas, cantidades, marker='o')
#     plt.title("Unidades producidas por día")
#     plt.xlabel("Fecha")
#     plt.ylabel("Unidades")
#     st.pyplot(plt)

# ===== Gráfica mejorada: Producción por producto =====
if sim.production_log:
    st.markdown("## Producción por Producto por Día")
    from collections import defaultdict
    import matplotlib.pyplot as plt

    produccion_por_dia = defaultdict(lambda: defaultdict(int))
    for log in sim.production_log:
        for pid, qty in log.get("produced", {}).items():
            produccion_por_dia[pid][log["date"]] += qty

    for pid, fechas_qty in produccion_por_dia.items():
        fechas = sorted(fechas_qty.keys())
        cantidades = [fechas_qty[fecha] for fecha in fechas]
        plt.figure()
        plt.plot(fechas, cantidades, marker='o')
        st.pyplot(plt)
