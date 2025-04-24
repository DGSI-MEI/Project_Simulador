# Simulador de Producción de Impresoras 3D - Contexto del Proyecto

## ¿Qué estamos construyendo?
Un simulador de producción para una planta que fabrica impresoras 3D, donde el usuario actúa como planificador de producción. El sistema permite:
- Simular la producción día a día
- Gestionar inventarios
- Realizar compras a proveedores
- Planificar la producción
- Visualizar estadísticas y métricas

## Tareas Completadas ✅
1. **Estructura Base del Proyecto**
   - Organización inicial de carpetas
   - Configuración del entorno de desarrollo

2. **Modelos de Datos (usando Pydantic)**
   - Product (productos y materias primas)
   - BOM (lista de materiales)
   - Supplier (proveedores)
   - InventoryItem (gestión de inventario)
   - ProductionOrder (órdenes de producción)
   - PurchaseOrder (órdenes de compra)
   - Event (registro de eventos)
   - ProductionPlan (configuración de producción)
   - SimulationConfig (configuración de simulación)
   - DailyStats (estadísticas diarias)

3. **Sistema de Persistencia**
   - Implementación de almacenamiento basado en JSON
   - Sistema de respaldo (backup)
   - Operaciones CRUD básicas

## Tareas Pendientes 📝
1. **Simulación**
   - Implementar el motor de simulación con SimPy
   - Desarrollar la lógica de generación de demanda
   - Crear sistema de eventos discretos

2. **API Backend**
   - Desarrollar endpoints REST con FastAPI
   - Implementar documentación con Swagger/OpenAPI
   - Crear validaciones y manejo de errores

3. **Interfaz de Usuario**
   - Crear dashboard con Streamlit
   - Implementar visualizaciones con matplotlib
   - Desarrollar paneles de control interactivos

4. **Testing**
   - Crear tests unitarios
   - Implementar tests de integración
   - Desarrollar escenarios de prueba

5. **Documentación**
   - Manual de usuario
   - Documentación técnica
   - Guías de instalación y despliegue

## Decisiones Técnicas 🛠

### Lenguaje Principal
- **Python 3.11/3.12**: Elegido por su simplicidad y amplio soporte en simulación y análisis de datos

### Frameworks y Bibliotecas
1. **Backend**
   - FastAPI: Para la API REST
   - Pydantic: Para validación de datos y serialización
   - SimPy: Motor de simulación de eventos discretos

2. **Frontend**
   - Streamlit: Para crear la interfaz de usuario
   - Matplotlib: Para visualizaciones y gráficos

3. **Persistencia**
   - Sistema basado en JSON: Por su simplicidad y portabilidad
   - Estructura modular para futura migración a BD si es necesario

### Estructura del Proyecto
