# Archivo: models/usuario.py
from beanie import Document
from pydantic import EmailStr

class Usuario(Document):
    username: str
    nombre_completo: str
    email: EmailStr
    password_hash: str  # Guardaremos la contraseña encriptada, no la real
    rol: str = "tecnico" # roles: admin, tecnico, cajero
    activo: bool = True

    class Settings:
        name = "usuarios_sistema"