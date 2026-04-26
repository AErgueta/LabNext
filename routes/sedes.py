from fastapi import APIRouter, HTTPException
from models.sede import Sede
from typing import List

router = APIRouter()

@router.post("/", response_model=Sede)
async def crear_sede(sede: Sede):
    # Verificamos si ya existe una sede con ese nombre
    existe = await Sede.find_one(Sede.nombre == sede.nombre)
    if existe:
        raise HTTPException(status_code=400, detail="La sede ya está registrada")
    
    await sede.insert()
    return sede

@router.get("/", response_model=List[Sede])
async def listar_sedes():
    return await Sede.find_all().to_list()