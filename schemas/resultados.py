from pydantic import BaseModel
from typing import List

class ResultadoAnalito(BaseModel):
    analito_nombre: str
    valor: float  # Usamos float por si envían decimales como 14.5
    unidad: str
    estado_resultado: str = "Finalizado"

class PeticionCargaResultados(BaseModel):
    orden_id: str
    estudio_id: str
    resultados_por_analito: List[ResultadoAnalito]