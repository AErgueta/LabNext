# Archivo: models/usuario.py
from beanie import Document
from pydantic import BaseModel, EmailStr
from typing import Literal

# 1. Definimos los roles oficiales del laboratorio
RolUsuario = Literal["Admin", "Cajero", "TomadorMuestra", "Bioquimico"]

class Usuario(Document):
    username: str
    nombre_completo: str
    email: EmailStr
    password_hash: str  # Guardaremos la contraseña encriptada
    rol: RolUsuario     # Usamos la restricción estricta
    activo: bool = True

    class Settings:
        name = "usuarios_sistema"

# 2. Creamos el "Molde de Entrada" para crear usuarios desde la API
class UsuarioCreate(BaseModel):
    username: str
    nombre_completo: str
    email: EmailStr
    password: str       # Aquí entra la contraseña normal
    rol: RolUsuario