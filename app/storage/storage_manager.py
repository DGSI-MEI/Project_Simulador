from typing import List
from app.models.models import Product, InventoryItem, Supplier, ProductionOrder
from app.storage.json_storage import JsonStorage

class StorageManager:
    def __init__(self):
        self.storage = JsonStorage()
        
    def save_products(self, products: List[Product]):
        self.storage.save_collection("products", products)
        
    def load_products(self) -> List[Product]:
        return self.storage.load_collection("products", Product)
        
    def save_inventory(self, inventory: List[InventoryItem]):
        self.storage.save_collection("inventory", inventory)
        
    def load_inventory(self) -> List[InventoryItem]:
        return self.storage.load_collection("inventory", InventoryItem)
        
    def save_simulation_state(self, state: dict):
        self.storage.save_simulation_state(state)
        
    def load_simulation_state(self) -> dict:
        return self.storage.load_simulation_state() or {}
        
    def create_backup(self) -> str:
        return self.storage.backup_data()
