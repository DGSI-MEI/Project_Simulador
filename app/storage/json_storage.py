import json
import os
from datetime import datetime
from typing import Dict, List, Optional, TypeVar, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class JsonStorage:
    def __init__(self, data_dir: str = "data"):
        """
        Inicializa el sistema de almacenamiento JSON.
        
        Args:
            data_dir (str): Directorio donde se guardarán los archivos JSON
        """
        self.data_dir = data_dir
        self._ensure_data_directory()
        
    def _ensure_data_directory(self) -> None:
        """Asegura que existe el directorio de datos"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
    def _get_file_path(self, collection_name: str) -> str:
        """
        Obtiene la ruta completa para un archivo JSON.
        
        Args:
            collection_name (str): Nombre de la colección (ej: 'products', 'inventory')
            
        Returns:
            str: Ruta completa del archivo
        """
        return os.path.join(self.data_dir, f"{collection_name}.json")
    
    def save_collection(self, collection_name: str, data: List[BaseModel]) -> None:
        """
        Guarda una colección de modelos Pydantic en un archivo JSON.
        
        Args:
            collection_name (str): Nombre de la colección
            data (List[BaseModel]): Lista de modelos Pydantic a guardar
        """
        file_path = self._get_file_path(collection_name)
        json_data = [item.model_dump() for item in data]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, default=str)
            
    def load_collection(self, collection_name: str, model_class: Type[T]) -> List[T]:
        """
        Carga una colección desde un archivo JSON y la convierte en modelos Pydantic.
        
        Args:
            collection_name (str): Nombre de la colección
            model_class (Type[T]): Clase del modelo Pydantic
            
        Returns:
            List[T]: Lista de instancias del modelo Pydantic
        """
        file_path = self._get_file_path(collection_name)
        
        if not os.path.exists(file_path):
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [model_class.model_validate(item) for item in data]
            
    def save_simulation_state(self, state: Dict) -> None:
        """
        Guarda el estado completo de la simulación.
        
        Args:
            state (Dict): Estado de la simulación
        """
        file_path = self._get_file_path("simulation_state")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, default=str)
            
    def load_simulation_state(self) -> Optional[Dict]:
        """
        Carga el estado de la simulación.
        
        Returns:
            Optional[Dict]: Estado de la simulación o None si no existe
        """
        file_path = self._get_file_path("simulation_state")
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def backup_data(self) -> str:
        """
        Crea una copia de seguridad de todos los datos.
        
        Returns:
            str: Nombre del directorio de backup
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.data_dir, f"backup_{timestamp}")
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        for file_name in os.listdir(self.data_dir):
            if file_name.endswith('.json'):
                source = os.path.join(self.data_dir, file_name)
                destination = os.path.join(backup_dir, file_name)
                with open(source, 'r', encoding='utf-8') as src, \
                     open(destination, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                    
        return backup_dir
