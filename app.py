import streamlit as st
from simulator import Simulator
from models import Product, InventoryItem, Order, BOMItem, Supplier, PurchaseOrder, Event
import simpy
from datetime import date, timedelta, datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

import pandas as pd
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
        "orders": [o.dict() | {"creation_date": o.creation_date.isoformat(),
                       "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None,
                       "initial_quantity": o.initial_quantity}
            for o in sim.orders],
        "purchase_orders": [
            po.dict() | {
                "order_date": po.order_date.isoformat(),
                "expected_arrival": po.expected_arrival.isoformat()
            } for po in sim.purchase_orders
        ],
        "events": [e.dict() | {"sim_date": e.sim_date.isoformat()} for e in sim.events],
        "inventory_history": [
            {
                "date": entry["date"].isoformat(),
                "inventory": entry["inventory"]
            }
            for entry in sim.inventory_history
        ],
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
            sim.orders = [Order(**{
                **o,
                "creation_date": datetime.fromisoformat(o["creation_date"]).date(),
                "delivery_date": datetime.fromisoformat(o["delivery_date"]).date() if o.get("delivery_date") else None,
                "initial_quantity": o.get("initial_quantity", o["quantity"])

            }) for o in estado["orders"]]
            sim.purchase_orders = [
                PurchaseOrder(**{
                    **po,
                    "order_date": datetime.fromisoformat(po["order_date"]).date(),
                    "expected_arrival": datetime.fromisoformat(po["expected_arrival"]).date()
                }) for po in estado["purchase_orders"]
            ]
            sim.events = [Event(**{**e, "sim_date": datetime.fromisoformat(e["sim_date"]).date()}) for e in estado["events"]]
            sim.inventory_history = [{
                    "date": datetime.fromisoformat(entry["date"]).date(),
                    "inventory": {int(k): v for k, v in entry["inventory"].items()}
                }
                for entry in estado.get("inventory_history", [])
            ]
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
    sim.generar_pedidos()
    sim.generar_pedidos()

    guardar_estado(sim)


# 3. Cargar estado una única vez, después de posible inicialización
cargar_estado(sim)

# ===== Lógica MRP =====
def calcular_faltantes():
    requerimientos = defaultdict(int)

    # Paso 1: sumar materiales requeridos por pedidos pendientes
    for order in sim.orders:
        if order.status == "pending":
            for bom in sim.boms:
                if bom.finished_product_id == order.product_id:
                    requerimientos[bom.material_id] += bom.quantity * order.quantity

    # Paso 2: restar materiales que ya están comprometidos en pedidos liberados
    reservas = defaultdict(int)
    for order in sim.orders:
        if order.status == "released":
            for bom in sim.boms:
                if bom.finished_product_id == order.product_id:
                    reservas[bom.material_id] += bom.quantity * order.quantity

    # Paso 3: calcular faltantes reales
    faltantes = {}
    for pid, req_qty in requerimientos.items():
        en_stock = sim.inventory.get(pid, 0)
        reservado = reservas.get(pid, 0)
        disponible = en_stock - reservado

        if req_qty > disponible:
            faltantes[pid] = req_qty - disponible

    return faltantes

def calcular_faltantes_by_order(order):
    # Copiamos el inventario actual
    inventario_disponible = sim.inventory.copy()

    # Reservamos materiales para pedidos ya liberados (que aún no se han completado)
    for o in sim.orders:
        if o.status == "released" and o.id != order.id:
            for bom in sim.boms:
                if bom.finished_product_id == o.product_id:
                    inventario_disponible[bom.material_id] -= bom.quantity * o.quantity

    # Requerimientos del pedido actual
    requerimientos = defaultdict(int)
    for bom in sim.boms:
        if bom.finished_product_id == order.product_id:
            requerimientos[bom.material_id] += bom.quantity * order.quantity

    # Calcular faltantes reales
    faltantes = {}
    for pid, req_qty in requerimientos.items():
        en_stock = inventario_disponible.get(pid, 0)
        if req_qty > en_stock:
            faltantes[pid] = req_qty - en_stock

    return faltantes


# ===== Encabezado =====
st.title("Simulador MRP - Producción Impresoras 3D")
st.subheader(f"Día simulado: {sim.day} ({sim.current_date})")

# Inicializar valores por defecto si no existen
if "media" not in st.session_state:
    st.session_state["media"] = 5
if "desviacion" not in st.session_state:
    st.session_state["desviacion"] = 2

# Configuración avanzada
with st.expander("⚙️ Configuración avanzada de generación de pedidos"):
    st.session_state["media"] = st.slider("Media de pedidos diarios", 1, 20, st.session_state["media"])
    st.session_state["desviacion"] = st.slider("Desviación estándar de cantidad", 1, 10, st.session_state["desviacion"])
    st.session_state["tiempo_base_entrega"] = st.slider("Tiempo base de entrega (días)", 1, 10, st.session_state.get("tiempo_base_entrega", 3))

media = st.session_state["media"]
desviacion = st.session_state["desviacion"]
tiempo_base_entrega = st.session_state["tiempo_base_entrega"]

#
with st.expander("🏭 Configuración avanzada: capacidad de producción"):
    st.session_state["capacidad_produccion"] = st.slider(
        "Capacidad de producción diaria (unidades)", 1, 50, st.session_state.get("capacidad_produccion", 10)
    )

sim.daily_capacity = st.session_state["capacidad_produccion"]


# Botón para avanzar día
if st.button("▶️ Avanzar Día"):
    sim.advance_day(media=media, desviacion=desviacion,tiempo_base_entrega=tiempo_base_entrega)
    guardar_estado(sim)
    st.success("Día avanzado y estado guardado")
    st.rerun()


# ===== Panel Pedidos =====
st.markdown("## 📦 Pedidos Pendientes")

with st.expander("📉 Ver resumen avanzado de faltantes globales"):
    faltantes = calcular_faltantes()

    if faltantes:
        materiales_faltantes = []
        resumen_proveedores = []

        for pid, qty in faltantes.items():
            product = next((p for p in sim.products if p.id == pid and p.type == "raw"), None)
            if not product:
                continue

            proveedores = [s for s in sim.suppliers if s.product_id == pid]
            if proveedores:
                proveedor_sugerido = min(proveedores, key=lambda p: p.lead_time)
                proveedor_nombre = proveedor_sugerido.name
                lead = proveedor_sugerido.lead_time
            else:
                proveedor_sugerido = None
                proveedor_nombre = "N/D"
                lead = "—"

            materiales_faltantes.append({
                "ID": pid,
                "Nombre": product.name,
                "Cantidad": qty,
                "Proveedor sugerido": proveedor_nombre,
                "Lead time (días)": lead
            })

        df_faltantes = pd.DataFrame(materiales_faltantes)
        st.dataframe(df_faltantes, use_container_width=True, hide_index=True)

        if st.button("🛒 Comprar todo lo que falta"):
            for item in materiales_faltantes:
                proveedores = [s for s in sim.suppliers if s.product_id == item["ID"]]
                if not proveedores:
                    continue

                proveedor = min(proveedores, key=lambda p: p.lead_time)
                cantidad = item["Cantidad"]

                nuevo_po = PurchaseOrder(
                    id=len(sim.purchase_orders) + 1,
                    supplier_id=proveedor.id,
                    product_id=item["ID"],
                    quantity=cantidad,
                    unit_cost=proveedor.unit_cost,
                    order_date=sim.current_date,
                    expected_arrival=sim.current_date + timedelta(days=proveedor.lead_time),
                    status="ordered"
                )
                sim.purchase_orders.append(nuevo_po)

                sim.log_event(
                    event_type="purchase",
                    description="Compra global desde faltantes",
                    product_id=item["ID"],
                    quantity=cantidad,
                    extra={
                        "proveedor": proveedor.name,
                        "lead_time": proveedor.lead_time
                    }
                )

                resumen_proveedores.append(
                    f"- {item['Nombre']} → {proveedor.name} ({proveedor.lead_time} días)"
                )

            guardar_estado(sim)
            st.success("✅ Órdenes de compra generadas por todos los materiales faltantes")
            st.markdown("### 🧾 Proveedores seleccionados automáticamente:")
            for linea in resumen_proveedores:
                st.markdown(linea)
            st.rerun()
    else:
        st.info("No hay faltantes para los pedidos actuales.")


# Recorrer pedidos pendientes
for order in sim.orders:
    if order.status != "pending":
        continue

    product = next((p for p in sim.products if p.id == order.product_id), None)
    product_name = product.name if product else "Desconocido"

    # Mostrar resumen del pedido
    col1, col2, col3, col4, col5 = st.columns([1.5, 3, 2, 3, 1.5])
    col1.write(f"**#{order.id}**")
    col2.write(f"{product_name}")
    col3.write(f"{order.quantity} unidades")


    # Evaluar retraso
    entrega = order.delivery_date.strftime("%Y-%m-%d") if order.delivery_date else "N/D"
    retrasado = order.delivery_date and sim.current_date > order.delivery_date

    if retrasado:
        col4.markdown(f"<span style='color:red;'>📅 {entrega} (retrasado)</span>", unsafe_allow_html=True)
    else:
        col4.markdown(f"📅 {entrega}")

    if col5.button("🔍 Detalles", key=f"btn_detalle_{order.id}"):
        st.session_state[f"mostrar_detalle_{order.id}"] = not st.session_state.get(f"mostrar_detalle_{order.id}", False)

    if st.session_state.get(f"mostrar_detalle_{order.id}", False):
        st.markdown(f"### 📄 Detalles del Pedido #{order.id} - {product_name}")
        fecha_entrega = order.delivery_date.strftime("%Y-%m-%d") if order.delivery_date else "No especificada"
        st.markdown(f"📆 **Entrega estimada:** {fecha_entrega}")
        # Obtener materiales del BOM para ese producto
        materiales = [b for b in sim.boms if b.finished_product_id == order.product_id]
        bom_data = []

        for mat in materiales:
            total = mat.quantity * order.quantity
            en_stock = sim.inventory.get(mat.material_id, 0)
            faltan = max(0, total - en_stock)
            bom_data.append({
                "Material ID": mat.material_id,
                "Cantidad x unidad": mat.quantity,
                "Total requerido": total,
                "En inventario": en_stock,
                "Faltan": faltan,
            })

        st.markdown("#### 📋 Lista de materiales requeridos")
        df_bom = pd.DataFrame(bom_data)
        st.dataframe(df_bom, use_container_width=True, hide_index=True)

        # Mostrar sección para faltantes
        for item in bom_data:
            if item["Faltan"] > 0:
                st.markdown(f"**🔧 Acción requerida: Material {item['Material ID']}**")

                with st.expander(f"🛒 Comprar {item['Faltan']} unidades", expanded=False):
                    proveedores = [s for s in sim.suppliers if s.product_id == item["Material ID"]]

                    if not proveedores:
                        st.warning("⚠️ No hay proveedores disponibles para este material.")
                        continue

                    proveedor_opciones = {
                        f"{p.name} (lead time: {p.lead_time} días)": p for p in proveedores
                    }

                    seleccion = st.selectbox(
                        "Selecciona proveedor:",
                        options=list(proveedor_opciones.keys()),
                        key=f"select_proveedor_{order.id}_{item['Material ID']}"
                    )

                    proveedor = proveedor_opciones[seleccion]
                    costo_total = item["Faltan"] * proveedor.unit_cost
                    st.write(f"💰 Costo estimado: {item['Faltan']} x {proveedor.unit_cost:.2f} = {costo_total:.2f}")

                    if st.button("Confirmar compra", key=f"confirmar_compra_{order.id}_{item['Material ID']}"):
                        nuevo_po = PurchaseOrder(
                            id=len(sim.purchase_orders) + 1,
                            supplier_id=proveedor.id,
                            product_id=item["Material ID"],
                            quantity=item["Faltan"],
                            unit_cost=proveedor.unit_cost,
                            order_date=sim.current_date,
                            expected_arrival=sim.current_date + timedelta(days=proveedor.lead_time),
                            status="ordered" 
                        )
                        sim.purchase_orders.append(nuevo_po)
                        sim.log_event("purchase", f"Pedido de compra generado: {item['Faltan']} x de Material (ID:{item['Material ID']}) al proveedor {proveedor.name}")
                        guardar_estado(sim)
                        st.success(f"✅ Pedido de compra registrado con {proveedor.name}")
                        st.rerun()

        # Si no hay faltantes, permitir liberar el pedido
        faltantes = calcular_faltantes_by_order(order)
        if not faltantes:
            if st.button(f"✅ Liberar pedido #{order.id}", key=f"liberar_{order.id}"):
                order.status = "released"
                sim.log_event("stock", f"Pedido #{order.id} liberado para producción.")
                guardar_estado(sim)
                st.rerun()

        st.divider()





# ===== Panel Inventario =====
st.markdown("## Inventario")


st.markdown("### Materiales")
materiales_data = []
for pid, qty in sim.inventory.items():
    product = next((p for p in sim.products if p.id == pid and p.type == "raw"), None)
    if product:
        materiales_data.append({"ID": pid, "Nombre": product.name, "Cantidad": qty})

if materiales_data:
    df_materiales = pd.DataFrame(materiales_data)
    st.dataframe(df_materiales.style.hide(axis="index"),hide_index=True)
else:
    st.info("No se dispone de materiales")

st.markdown("### Productos terminados")
productos_data = []
for pid, qty in sim.inventory.items():
    product = next((p for p in sim.products if p.id == pid and p.type == "finished"), None)
    if product:
        productos_data.append({"ID": pid, "Nombre": product.name, "Cantidad": qty})

if productos_data:
    df_productos = pd.DataFrame(productos_data)
    st.dataframe(df_productos.style.hide(axis="index"), hide_index=True) 
else:
    st.info("No se dispone de productos")


# st.markdown("### Debug: Órdenes y estado")
# for order in sim.orders:
#     st.text(f"[DEBUG] Pedido {order.id} - Estado: {order.status} - Cantidad: {order.quantity}")

# st.markdown("### Debug: Inventario actual")
# for pid, qty in sim.inventory.items():
#     st.text(f"[DEBUG] Producto {pid} -> Stock: {qty}")


# ===== Panel Compras =====
# st.markdown("## Emitir Orden de Compra")
# producto_ids = list(set(s.product_id for s in sim.suppliers))
# producto_seleccionado = st.selectbox("Producto", producto_ids)
# proveedores_disponibles = [s for s in sim.suppliers if s.product_id == producto_seleccionado]
# nombres_proveedores = [f"{s.id} - {s.name} (Lead Time: {s.lead_time} días)" for s in proveedores_disponibles]
# proveedor_elegido_idx = st.selectbox("Proveedor", list(range(len(nombres_proveedores))), format_func=lambda i: nombres_proveedores[i])
# cantidad = st.number_input("Cantidad a comprar", min_value=1, step=1)

# if st.button("Emitir Orden"):
#     proveedor = proveedores_disponibles[proveedor_elegido_idx]
#     fecha_entrega = sim.current_date + timedelta(days=proveedor.lead_time)
#     nueva_oc = PurchaseOrder(
#         id=len(sim.purchase_orders) + 1,
#         supplier_id=proveedor.id,
#         product_id=proveedor.product_id,
#         quantity=cantidad,
#         order_date=sim.current_date,
#         expected_arrival=fecha_entrega,
#         status="ordered"
#     )
#     sim.purchase_orders.append(nueva_oc)
#     sim.log_event("purchase", f"Orden de compra creada: {cantidad} unidades del producto {proveedor.product_id} al proveedor {proveedor.name}.")
#     guardar_estado(sim)
#     st.success("Orden de compra emitida")
#===== Órdenes de Compra Emitidas =====
st.markdown("## 📑 Órdenes de Compra Emitidas")

if sim.purchase_orders:
    tabla_oc = []
    for po in sim.purchase_orders:
        proveedor = next((s.name for s in sim.suppliers if s.id == po.supplier_id), "Desconocido")
        producto = next((p.name for p in sim.products if p.id == po.product_id), f"ID {po.product_id}")
        tabla_oc.append({
            "OC #": po.id,
            "Producto": producto,
            "Proveedor": proveedor,
            "Cantidad": po.quantity,
            "Fecha de orden": po.order_date.strftime("%Y-%m-%d"),
            "Fecha estimada llegada": po.expected_arrival.strftime("%Y-%m-%d"),
            "Estado": po.status
        })

    df_oc = pd.DataFrame(tabla_oc)
    st.dataframe(df_oc, use_container_width=True, hide_index=True)
else:
    st.info("No hay órdenes de compra registradas.")


# ===== Panel Producción =====
st.markdown("## Producción")
st.write(f"Capacidad diaria: {sim.daily_capacity} unidades")


st.markdown("## ✅ Pedidos Completados")

pedidos_completados = [o for o in sim.orders if o.status == "completed"]

if pedidos_completados:
    tabla = []
    for order in pedidos_completados:
        product_name = next((p.name for p in sim.products if p.id == order.product_id), f"ID {order.product_id}")
        cantidad_total = order.initial_quantity or order.quantity

        fila = {
            "Pedido #": order.id,
            "Producto": product_name,
            "Cantidad producida": cantidad_total,
            "Fecha de entrega estimada": order.delivery_date.strftime("%Y-%m-%d") if order.delivery_date else "N/D",
            "Estado": "✅ Completado"
        }
        tabla.append(fila)

    df = pd.DataFrame(tabla)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No hay pedidos completados aún.")

st.markdown("## 🏭 Pedidos en Producción (Liberados)")

pedidos_en_produccion = [o for o in sim.orders if o.status == "released"]

if pedidos_en_produccion:
    tabla = []
    for order in pedidos_en_produccion:
        product_name = next((p.name for p in sim.products if p.id == order.product_id), f"ID {order.product_id}")
        cantidad_total = order.initial_quantity or order.quantity
        cantidad_restante = order.quantity
        cantidad_producida = cantidad_total - cantidad_restante
        estado = "🔄 Parcial" if cantidad_producida > 0 else "⏳ Esperando"
        cantidad_total = order.initial_quantity or order.quantity
  
        progreso = cantidad_producida / cantidad_total if cantidad_total > 0 else 0
        barra = f"[{'█' * int(progreso * 10):<10}] {int(progreso * 100)}%"

        fila = {
            "Pedido #": order.id,
            "Producto": product_name,
            "Producido": cantidad_producida,
            "Restante": cantidad_restante,
            "Progreso": barra,
            "Estado": estado
        }
        tabla.append(fila)

    df = pd.DataFrame(tabla)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No hay pedidos liberados en cola de producción.")




# ===== Gráficas =====

st.markdown("## 📊 Visualización de Datos")
with st.expander("📦 Inventario histórico de materiales (gráfico de línea)"):
    if sim.inventory_history:
        df_inv = pd.DataFrame(sim.inventory_history)  # cada entrada: {'date': date, 'inventory': {product_id: qty}}

        # Convertimos a estructura tipo DataFrame con fechas como índice
        data_por_material = {}
        for entrada in sim.inventory_history:
            fecha = entrada["date"]
            for pid, cantidad in entrada["inventory"].items():
                data_por_material.setdefault(pid, []).append((fecha, cantidad))

        # Selección de producto para graficar
        pids_disponibles = list(data_por_material.keys())
        productos_dict = {p.id: p.name for p in sim.products}
        nombre_productos = [f"{pid} - {productos_dict.get(pid, 'Desconocido')}" for pid in pids_disponibles]
        seleccion = st.selectbox("Selecciona material:", nombre_productos)
        pid_seleccionado = int(seleccion.split(" - ")[0])

        datos = data_por_material[pid_seleccionado]
        fechas, cantidades = zip(*datos)

        fig, ax = plt.subplots()
        ax.plot(fechas, cantidades, marker='o')
        ax.set_title(f"Inventario de {productos_dict.get(pid_seleccionado, 'Desconocido')}")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Unidades")
         # Formatear eje X para mostrar solo día y mes
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        fig.autofmt_xdate()  # rota ligeramente las etiquetas

        ax.grid(True)
        st.pyplot(fig)
    else:
        st.info("Aún no hay historial de inventario para graficar.")