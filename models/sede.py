from typing import Annotated
from beanie import Document, Indexed

class Sede(Document):
    pais: str = "Bolivia"
    ciudad: str = "Santa Cruz"
    nombre: Annotated[str, Indexed(unique=True)] # Ejemplo: "Equipetrol" o "Sucursal Centro"
    direccion: str
    # Este campo es clave para la logística que mencionaste:
    es_procesadora: bool = True # Si es False, significa que solo toma muestras y debe enviarlas a otra sede

    class Settings:
        name = "sedes"