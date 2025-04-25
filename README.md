# Simulador MRP - Producción de Impresoras 3D

## Descripción General
Este proyecto implementa un sistema de Planificación de Requerimientos de Materiales (MRP) para una fábrica de impresoras 3D. Está desarrollado con Python y Streamlit, simulando de forma visual e interactiva el flujo completo de materiales, órdenes de compra, pedidos y producción diaria.

---

## Componentes del Proyecto

### Archivos Principales
- `app.py`: Interfaz Streamlit e interacción con el usuario.
- `simulator.py`: Lógica del simulador MRP.
- `models.py`: Modelado de datos con Pydantic.
- `data/configuracion.json`: Catálogo de productos, BOMs y proveedores.
- `data/estado.json`: Archivo persistente con el estado del sistema.
- `requirements.txt`: Dependencias necesarias.

---

## Flujo del Sistema

### 1. Simulación por Día
- Avance diario controlado por el usuario.
- Se ejecutan eventos: producción, compras, generación de nuevos pedidos.

### 2. Producción
- Requiere que el usuario libere pedidos.
- Respeta capacidad diaria.
- Consume materiales según la lista BOM.

### 3. Compras
- Emisión manual o automática de órdenes.
- Se respetan los tiempos de entrega de cada proveedor.

### 4. Inventario
- Materias primas y productos terminados.
- Inventario inicial aleatorio (entre 5 y 20 unidades por materia prima).

### 5. Pedidos
- Se generan 2 pedidos iniciales aleatorios.
- Nuevos pedidos se generan automáticamente cada día.

---

## Visualizaciones en la Interfaz
- Encabezado: Día simulado y botón Avanzar Día.
- Panel de Pedidos: Lista de pedidos pendientes, liberación manual.
- Panel de Inventario: Niveles actuales, faltantes detectados.
- Panel de Compras: Selección de producto, proveedor, cantidad.
- Panel de Producción: Pedidos en cola, capacidad diaria.
- Gráficas:
  - Producción por producto por día
  - Stock histórico por producto

---

## Persistencia y Estado
- El estado se guarda automáticamente al avanzar el día.
- Se carga al iniciar la app si existe `estado.json`.
- Compatible con sesiones múltiples y reinicios.

---

## Fases del Desarrollo

### Fase 1: Análisis de Requerimientos
- Revisión del PDF de especificaciones.
- Identificación de módulos: producción, compras, inventario, pedidos, eventos.

### Fase 2: Estructura Base
- Creación de clases con Pydantic.
- Generación del simulador base (avance de día, lógica de eventos).

### Fase 3: Interfaz Streamlit
- Visualización de inventario, pedidos, eventos.
- Paneles de control para usuario.

### Fase 4: Persistencia y Estados
- Guardado en JSON del estado del sistema.
- Inicialización controlada solo si no existe estado previo.

### Fase 5: Estadísticas y Mejora de Producción
- Producción detallada por producto.
- Gráficas de evolución por día.

### Fase 6: Flexibilidad de carga datos de configuración
- Inventario inicial aleatorio.
- Órdenes iniciales aleatorias.

### Fase 7: Exportaciones y mejoras visuales del Dashboard
- Exportabilidad prevista (JSON, tablas).
- Mejor las distribución de las pantallas de información

### Fase 8: Documentación 
- Agregar al codigo las explicaciones de su comportamiento
- Documentación detallada de las implementación e informe. 

### Fase 9: Presentación
- Resumen 
---

## Cómo Ejecutar
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Créditos
Proyecto desarrollado para el MEI UPC - DGSI, 2025.

Autores:  Kenny Alejandro, Javier Abella, Xinlei Lin, Zhiwei Lin



