import os
import bcrypt
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Importar los routers
from routes.pacientes import router as pacientes_router
from routes.estudios import router as estudios_router  # <-- Módulo de Estudios agregado

# Importar los modelos
from models.usuario import Usuario 
from models.paciente import Paciente
from models.estudio import Estudio  # <-- Modelo de Estudios agregado

load_dotenv()

# --- MANEJO DE INICIO DE APLICACIÓN (LIFESPAN) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Todo lo que está antes del 'yield' se ejecuta al arrancar el servidor
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client["LabNext"]
    
    # Inicializamos Beanie con TODOS los modelos
    await init_beanie(database=db, document_models=[Usuario, Paciente, Estudio]) # <-- Estudio incluido en la lista
    print("✅ Base de datos conectada correctamente")
    
    yield  # Aquí la aplicación se queda corriendo esperando usuarios
    
    # Lo que pongas después del 'yield' se ejecuta al apagar el servidor
    print("🛑 Servidor LabNext detenido.")

# Se lo asignamos a la aplicación al crearla
app = FastAPI(title="LabNext", lifespan=lifespan)

# Configuración de archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- RUTAS DE AUTENTICACIÓN CON JINJA2 ---

@app.get("/login")
async def mostrar_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )

@app.post("/login")
async def procesar_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    usuario = await Usuario.find_one(Usuario.username == username)
    
    if not usuario:
        return templates.TemplateResponse(
            request=request, name="login.html", context={"error": "Usuario o contraseña incorrectos"}
        )

    password_bytes = password.encode('utf-8')
    hash_bytes = usuario.password_hash.encode('utf-8')
    
    if not bcrypt.checkpw(password_bytes, hash_bytes):
        return templates.TemplateResponse(
            request=request, name="login.html", context={"error": "Usuario o contraseña incorrectos"}
        )
    
    if not usuario.activo:
        return templates.TemplateResponse(
            request=request, name="login.html", context={"error": "El usuario se encuentra inactivo"}
        )

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="session_user", value=usuario.username, httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("session_user")
    return response

# --- RUTA PRINCIPAL ---

@app.get("/")
async def inicio(request: Request):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # Obtenemos el usuario de la BD
    usuario_db = await Usuario.find_one(Usuario.username == session_user)
    
    nombre_mostrar = usuario_db.nombre_completo if (usuario_db and usuario_db.nombre_completo) else session_user
    rol_usuario = usuario_db.rol if usuario_db else "Usuario"

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "usuario": nombre_mostrar,
            "rol": rol_usuario,
            "mensaje": f"¡Bienvenido {nombre_mostrar}! Sistema LabNext conectado con Jinja2."
        }
    )

# --- REGISTRO DE MÓDULOS (ROUTERS) ---
app.include_router(pacientes_router)
app.include_router(estudios_router) # <-- Router de Estudios registrado

# --- ARRANCADOR DEL SERVIDOR ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)