from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Annotated
from beanie import Document, Indexed, PydanticObjectId


# --- 2A. Submodelo para el Historial (Event Sourcing) ---
class EventoTracking(BaseModel):
    estado: str 
    # Registramos el momento exacto (no se puede modificar)
    fecha_hora: datetime = Field(default_factory=datetime.now) 
    # Guardamos el username de quien escaneó (viene de tu seguridad.py)
    usuario: str 
    # El ID de la Sede (Ej: Equipetrol) donde se hizo el bip
    sede_id: PydanticObjectId 
    observaciones: Optional[str] = None

# --- 2B. Modelo Principal de la Muestra ---
class Muestra(Document):
    # Indexed(unique=True) asegura que nunca haya dos tubos con el mismo código
    codigo_barras: Annotated[str, Indexed(unique=True)]
    
    # Vínculos funcionales
    orden_id: PydanticObjectId 
    flujo_id: PydanticObjectId # Sabe a qué "Mapa de Reglas" debe obedecer
    
    tipo_muestra: str # Ej: "Suero", "Sangre Total", "Orina"
    
    # Tracking
    estado_actual: str 
    historial_tracking: List[EventoTracking] = []

    class Settings:
        name = "muestras"