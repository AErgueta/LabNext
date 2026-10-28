from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from models.estudio import Estudio
from models.usuario import Usuario
from beanie import PydanticObjectId

# Configuramos el router con su prefijo
router = APIRouter(prefix="/estudios", tags=["Estudios"])
templates = Jinja2Templates(directory="templates")

# --- FUNCIÓN AUXILIAR DE SESIÓN (Basada en cookies) ---
async def obtener_usuario_sesion(request: Request):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return None
    return await Usuario.find_one(Usuario.username == session_user)

# --- 1. LISTAR ESTUDIOS (Vista HTML) ---
@router.get("/")
async def listar_estudios(request: Request, error: str = None):
    usuario_db = await obtener_usuario_sesion(request)
    if not usuario_db:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    estudios = await Estudio.find_all().to_list()
    
    return templates.TemplateResponse(
        request=request,
        name="estudios/index.html",
        context={
            "usuario": usuario_db.nombre_completo or usuario_db.username,
            "rol": usuario_db.rol,
            "estudios": estudios,
            "error": error
        }
    )

# --- 2. MOSTRAR FORMULARIO DINÁMICO (Vista HTML) ---
@router.get("/nuevo")
async def nuevo_estudio(request: Request):
    usuario_db = await obtener_usuario_sesion(request)
    
    # Validamos que esté logeado y sea Admin (solo Admin crea estudios)
    if not usuario_db or usuario_db.rol != "Admin":
        return RedirectResponse(url="/estudios?error=No+tienes+permisos+para+crear+estudios", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request=request,
        name="estudios/formulario.html",
        context={
            "usuario": usuario_db.nombre_completo or usuario_db.username,
            "rol": usuario_db.rol
        }
    )

# --- 3. API PARA GUARDAR ESTUDIO (Recibe JSON) ---
@router.post("/api/guardar")
async def guardar_estudio(estudio: Estudio, request: Request):
    usuario_db = await obtener_usuario_sesion(request)
    
    # Seguridad de backend para el endpoint API
    if not usuario_db or usuario_db.rol != "Admin":
        return JSONResponse(
            content={"status": "error", "message": "No autorizado para esta acción"}, 
            status_code=403
        )

    try:
        # Pydantic ya validó la estructura. Insertamos en MongoDB
        await estudio.insert()
        return JSONResponse(
            content={"status": "success", "id": str(estudio.id)}, 
            status_code=201
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)}, 
            status_code=400
        )

# --- 4. VISTA PARA EDITAR ESTUDIO ---
@router.get("/editar/{estudio_id}")
async def editar_estudio_view(request: Request, estudio_id: PydanticObjectId):
    usuario_db = await obtener_usuario_sesion(request)

    if not usuario_db or usuario_db.rol != "Admin":
        return RedirectResponse(url="/estudios?error=No+tienes+permisos", status_code=302)

    # Buscamos el estudio por su ID
    estudio = await Estudio.get(estudio_id)
    if not estudio:
        return RedirectResponse(url="/estudios?error=Estudio+no+encontrado", status_code=302)

    # Reutilizamos formulario.html, pero ahora le pasamos los datos
    return templates.TemplateResponse(
        request=request,
        name="estudios/formulario.html",
        context={
            "usuario": usuario_db.nombre_completo or usuario_db.username,
            "rol": usuario_db.rol,
            "estudio": estudio,
            # Pasamos el estudio en formato JSON para que JavaScript pueda armar los analitos
            "estudio_json": estudio.model_dump_json() 
        }
    )

# --- 5. API PARA ACTUALIZAR ESTUDIO ---
@router.put("/api/actualizar/{estudio_id}")
async def actualizar_estudio_api(estudio_id: PydanticObjectId, estudio_nuevo: Estudio, request: Request):
    usuario_db = await obtener_usuario_sesion(request)
    
    # Validamos que sea Admin
    if not usuario_db or usuario_db.rol != "Admin":
        return JSONResponse(content={"status": "error", "message": "No autorizado"}, status_code=403)

    # Buscamos el estudio existente en Atlas
    estudio_db = await Estudio.get(estudio_id)
    if not estudio_db:
        return JSONResponse(content={"status": "error", "message": "Estudio no encontrado"}, status_code=404)

    try:
        # Reemplazamos los datos antiguos por los nuevos que validó Pydantic
        await estudio_db.set(estudio_nuevo.model_dump(exclude_unset=True))
        return JSONResponse(content={"status": "success"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)


# --- 6. BÚSQUEDA EN VIVO (LIVE SEARCH) ---
@router.get("/buscar_live")
async def buscar_estudios_live(request: Request, q: str = ""):
    usuario_db = await obtener_usuario_sesion(request)
    if not usuario_db:
        return ""  # Seguridad: si no hay sesión, no devuelve nada

    # Si el usuario escribió algo, buscamos por CUPS o Nombre del Estudio
    if q:
        estudios = await Estudio.find(
            {"$or": [
                {"codigo_cups": {"$regex": q, "$options": "i"}},
                {"nombre_estudio": {"$regex": q, "$options": "i"}}
            ]}
        ).to_list()
    else:
        # Si la barra está vacía, devuelve el catálogo completo
        estudios = await Estudio.find_all().to_list()

    # Renderiza SOLO el archivo partial con las filas actualizadas
    return templates.TemplateResponse(
        request=request,
        name="estudios/filas_tabla.html",
        context={
            "estudios": estudios,
            "rol": usuario_db.rol
        }
    )