# Archivo: models/estudio.py
from pydantic import BaseModel
from typing import List, Optional
from beanie import Document

class RangoReferencia(BaseModel):
    sexo: str
    edad_min: int
    edad_max: int
    unidad_edad: str
    valor_min: Optional[float] = None
    valor_max: Optional[float] = None
    texto_referencia: Optional[str] = None

class Analito(BaseModel):
    nombre: str
    clave_interfaz: str
    unidad_medida: str
    tipo_resultado: str
    rangos: List[RangoReferencia]

class Estudio(Document):
    codigo_cups: str
    nombre_estudio: str
    seccion: str
    muestra: str
    # Días de la semana que el laboratorio corre la prueba (Ej: ["Lunes", "Miercoles"])
    dias_procesamiento: List[str] 
    # NUEVO CAMPO: Tiempo que tarda el estudio en estar listo (Ej: 2 días)
    dias_demora: int = 1
    
    analitos: List[Analito]
    precio_base: float

    class Settings:
        name = "catalogo_estudios"