from fastapi import APIRouter, HTTPException
from typing import List
from models.flujo_muestra import FlujoMuestra

router = APIRouter()

@router.post("/", response_model=FlujoMuestra)
async def crear_flujo_configuracion(flujo: FlujoMuestra):
    # Verificamos que no exista un flujo con el mismo nombre para no duplicar
    existe = await FlujoMuestra.find_one(FlujoMuestra.nombre_flujo == flujo.nombre_flujo)
    if existe:
        raise HTTPException(status_code=400, detail="Ya existe un flujo con este nombre")
    
    await flujo.insert()
    return flujo

@router.get("/", response_model=List[FlujoMuestra])
async def listar_flujos():
    return await FlujoMuestra.find_all().to_list()