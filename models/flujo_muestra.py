from typing import List, Dict
from beanie import Document

class FlujoMuestra(Document):
    nombre_flujo: str # Ej: "Flujo Estándar", "Derivaciones"
    descripcion: str
    
    # Lista de todos los estados que existen en este flujo
    estados_permitidos: List[str] 
    
    # El "candado lógico": Un diccionario que dicta qué estado puede ir hacia qué estado
    transiciones_validas: Dict[str, List[str]] 

    class Settings:
        name = "flujos_configuracion"