# Archivo: routes/medicos.py
from fastapi import APIRouter, Depends
from models.medico import Medico
# Importamos nuestros guardias
from utils.seguridad import verificar_token, verificar_admin

router = APIRouter()

# SOLO EL ADMIN puede registrar médicos nuevos
@router.post("/medicos")
async def crear_medico(medico: Medico, usuario: dict = Depends(verificar_admin)):
    await medico.insert()
    return {"status": "success", "message": f"Dr. {medico.nombre_completo} registrado"}

# CUALQUIER EMPLEADO logueado puede ver la lista de médicos (para llenar órdenes)
@router.get("/medicos")
async def listar_medicos(usuario: dict = Depends(verificar_token)):
    return await Medico.find_all().to_list()