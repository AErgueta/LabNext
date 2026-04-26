# Archivo: routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from models.usuario import Usuario
from utils.seguridad import encriptar_password, verificar_password, crear_token_acceso
from pydantic import BaseModel, EmailStr
from typing import Optional # Asegúrate de tener esta importación arriba

router = APIRouter()

# --- 1. RUTA PARA CREAR USUARIOS (Normalmente solo el Admin haría esto) ---
class UsuarioRegistro(BaseModel):
    username: str
    nombre_completo: str
    email: EmailStr
    password: str
    rol: str

class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None

@router.post("/usuarios/registrar")
async def registrar_usuario(user: UsuarioRegistro):
    # Verificamos que el username no exista ya
    existe = await Usuario.find_one(Usuario.username == user.username)
    if existe:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")

    # Creamos el usuario ENCRIPTANDO su contraseña antes de guardarla
    nuevo_usuario = Usuario(
        username=user.username,
        nombre_completo=user.nombre_completo,
        email=user.email,
        password_hash=encriptar_password(user.password),
        rol=user.rol
    )
    await nuevo_usuario.insert()
    return {"message": "Usuario creado exitosamente"}


# --- 2. RUTA DE LOGIN (Aquí es donde nos dan la Tarjeta Llave) ---
@router.post("/login")
async def iniciar_sesion(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Buscamos al usuario en la base de datos
    user = await Usuario.find_one(Usuario.username == form_data.username)
    
    # 2. Verificamos si existe y si su contraseña es correcta
    if not user or not verificar_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Si todo está bien, le creamos su Token (Tarjeta Llave)
    access_token = crear_token_acceso(data={"sub": user.username, "rol": user.rol})
    
    return {"access_token": access_token, "token_type": "bearer"}


# --- 3. RUTA PARA ACTUALIZAR/DESACTIVAR USUARIOS ---
@router.put("/usuarios/{username}")
async def actualizar_usuario(username: str, update_data: UsuarioUpdate):
    # 1. Buscamos al usuario en la base de datos
    user = await Usuario.find_one(Usuario.username == username)
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 2. Actualizamos solo los campos que el cliente nos envió
    if update_data.nombre_completo is not None:
        user.nombre_completo = update_data.nombre_completo
    if update_data.email is not None:
        user.email = update_data.email
    if update_data.rol is not None:
        user.rol = update_data.rol
    if update_data.activo is not None:
        user.activo = update_data.activo

    # 3. Guardamos los cambios en MongoDB
    await user.save()
    
    return {
        "status": "success", 
        "message": f"Usuario {username} actualizado",
        "estado_actual": "Activo" if user.activo else "Inactivo",
        "rol_actual": user.rol
    }