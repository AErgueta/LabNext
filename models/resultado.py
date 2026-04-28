# Archivo: models/resultado.py
from pydantic import BaseModel, Field
from typing import List, Optional
from beanie import Document, PydanticObjectId
from datetime import datetime

class ResultadoDetalle(BaseModel):
    analito: str             # Ej: "Glucosa Basal"
    valor_leido: float       # Ej: 115.5
    unidad_medida: str       # Ej: "mg/dL"
    estado_clinico: str      # "Normal", "Alto", "Bajo"
    rango_aplicado: str      # La "fotografía" del rango: "70 - 100 mg/dL (Normal Adulto)"
    fuera_de_rango: bool     # True si hay que ponerle una banderita roja de alerta

class ResultadoMuestra(Document):
    muestra_id: PydanticObjectId
    orden_id: PydanticObjectId
    estudio_nombre: str      # Ej: "Glucosa"
    
    resultados: List[ResultadoDetalle]
    
    bioquimico_validador: str
    fecha_procesamiento: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "resultados_clinicos"