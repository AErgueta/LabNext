# Archivo: routes/estudios.py
from fastapi import APIRouter, HTTPException, Depends
from models.estudio import Estudio
# 1. Traemos a ambos guardias
from utils.seguridad import verificar_token, verificar_admin

# Creamos un "mini-servidor" solo para estudios
router = APIRouter()

@router.post("/estudios")
async def crear_estudio(estudio: Estudio, usuario_actual: dict = Depends(verificar_admin)):
    await estudio.insert()
    return {"status": "success", "message": f"Estudio {estudio.nombre_estudio} guardado"}

@router.get("/estudios")
async def listar_estudios(usuario_actual: dict = Depends(verificar_token)):
    estudios = await Estudio.find_all().to_list()
    return estudios