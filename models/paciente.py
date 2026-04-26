# Archivo: models/paciente.py
from beanie import Document, Indexed, Link
from pydantic import EmailStr, Field
from datetime import datetime
from typing import Optional, Annotated 
from models.convenio import Convenio

class Paciente(Document):
    # CI con índice único
    ci: Annotated[str, Indexed(unique=True)] 
    
    nombre_completo: str
    fecha_nacimiento: datetime
    sexo: str  # "M" o "F"
    
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    
    tipo_paciente_default: str = "Particular" 
    convenio_predeterminado: Optional[Link[Convenio]] = None
    
    # LA SOLUCIÓN AL ERROR:
    # Ponemos el Field dentro del Annotated y también como valor por defecto.
    # Así Pylance entiende que 'datetime' es el tipo y lo demás es metadata.
    fecha_registro: Annotated[datetime, Field(default_factory=datetime.now)] = Field(default_factory=datetime.now)

    class Settings:
        name = "pacientes"