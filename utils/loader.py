from models import Product, BOMItem, Supplier
import json

def cargar_configuracion(filepath="data/configuracion.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = [Product(**p) for p in data.get("products", [])]
    boms = [BOMItem(**b) for b in data.get("boms", [])]
    suppliers = [Supplier(**s) for s in data.get("suppliers", [])]

    return products, boms, suppliers