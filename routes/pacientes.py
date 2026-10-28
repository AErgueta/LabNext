# Archivo: routes/pacientes.py
from fastapi import APIRouter, Request, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from models.paciente import Paciente
from models.usuario import Usuario
from datetime import datetime
from typing import Optional

# --- FUNCIÓN AUXILIAR PARA LA EDAD ---
def calcular_edad(fecha_nacimiento):
    if not fecha_nacimiento:
        return 0
    hoy = datetime.now()
    # Calcula la diferencia de años y resta 1 si aún no ha cumplido años este año
    return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])
templates = Jinja2Templates(directory="templates")

async def obtener_usuario_sesion(request: Request):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return None
    return await Usuario.find_one(Usuario.username == session_user)

# --- 1. MOSTRAR LISTADO Y BÚSQUEDA DE PACIENTES ---
@router.get("/")
async def listar_pacientes(request: Request, q: Optional[str] = None, error: Optional[str] = None):
    usuario_db = await obtener_usuario_sesion(request)
    if not usuario_db:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    nombre_mostrar = usuario_db.nombre_completo or usuario_db.username

    # Búsqueda dinámica por CI o Nombre Completo
    if q:
        pacientes_list = await Paciente.find(
            {"$or": [
                {"ci": {"$regex": q, "$options": "i"}},
                {"nombre_completo": {"$regex": q, "$options": "i"}}
            ]}
        ).to_list()
    else:
        pacientes_list = await Paciente.find_all().to_list()

    return templates.TemplateResponse(
        request=request,
        name="pacientes/index.html",
        context={
            "usuario": nombre_mostrar,
            "rol": usuario_db.rol,
            "pacientes": pacientes_list,
            "busqueda": q or "",
            "error": error,
            "calcular_edad": calcular_edad
        }
    )


# --- 1.5 BÚSQUEDA EN VIVO (LIVE SEARCH) ---
@router.get("/buscar_live")
async def buscar_pacientes_live(request: Request, q: str = ""):
    usuario_db = await obtener_usuario_sesion(request)
    if not usuario_db:
        return ""  # Seguridad: si no hay sesión activa, no devuelve datos
        
    # Si hay texto (q), busca coincidencias ignorando mayúsculas/minúsculas
    if q:
        pacientes_list = await Paciente.find(
            {"$or": [
                {"ci": {"$regex": q, "$options": "i"}},
                {"nombre_completo": {"$regex": q, "$options": "i"}}
            ]}
        ).to_list()
    else:
        # Si la barra está vacía, devuelve todos los pacientes
        pacientes_list = await Paciente.find_all().to_list()

    # Renderiza SOLO el archivo partial con las filas actualizadas
    return templates.TemplateResponse(
        request=request,
        name="pacientes/filas_tabla.html",
        context={
            "pacientes": pacientes_list,
            "rol": usuario_db.rol,
            "calcular_edad": calcular_edad
        }
    )

# --- 2. PROCESAR FORMULARIO DE REGISTRO ---
@router.post("/crear")
async def registrar_paciente(
    request: Request,
    ci: str = Form(...),
    nombre_completo: str = Form(...),
    fecha_nacimiento: str = Form(...), # Llega como YYYY-MM-DD desde el input date
    sexo: str = Form(...),             # "M" o "F"
    telefono: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    tipo_paciente_default: str = Form("Particular")
):
    usuario_db = await obtener_usuario_sesion(request)
    if not usuario_db:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # Validar duplicate de CI
    existe = await Paciente.find_one(Paciente.ci == ci)
    if existe:
        return RedirectResponse(
            url=f"/pacientes?error=El+paciente+con+CI+{ci}+ya+esta+registrado",
            status_code=status.HTTP_302_FOUND
        )

    # Convertir string de fecha HTML a objeto datetime
    fecha_dt = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")

    nuevo_paciente = Paciente(
        ci=ci.strip(),
        nombre_completo=nombre_completo.strip(),
        fecha_nacimiento=fecha_dt,
        sexo=sexo,
        telefono=telefono.strip() if telefono else None,
        email=email.strip() if email else None,
        tipo_paciente_default=tipo_paciente_default
    )
    await nuevo_paciente.insert()

    return RedirectResponse(url="/pacientes", status_code=status.HTTP_302_FOUND)


# --- 4. EDITAR PACIENTE ---
@router.post("/editar/{ci}")
async def editar_paciente(
    request: Request, 
    ci: str,
    nombre_completo: str = Form(...), 
    fecha_nacimiento: str = Form(...),
    sexo: str = Form(...), 
    telefono: Optional[str] = Form(None), 
    email: Optional[str] = Form(None)
):
    usuario_db = await obtener_usuario_sesion(request)
    if not usuario_db:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    # Buscamos el paciente
    paciente = await Paciente.find_one(Paciente.ci == ci)
    if paciente:
        # Actualizamos los datos
        paciente.nombre_completo = nombre_completo.strip()
        paciente.fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d")
        paciente.sexo = sexo
        paciente.telefono = telefono.strip() if telefono else None
        paciente.email = email.strip() if email else None
        
        # Guardamos en la base de datos
        await paciente.save()
        
    return RedirectResponse(url="/pacientes", status_code=status.HTTP_302_FOUND)