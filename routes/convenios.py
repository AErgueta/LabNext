# Archivo: routes/convenios.py
from fastapi import APIRouter
from models.convenio import Convenio

router = APIRouter()

@router.post("/convenios/")
async def crear_convenio(convenio: Convenio):
    await convenio.insert()
    return {"status": "success", "message": f"Convenio {convenio.nombre} ({convenio.tipo}) registrado"}

@router.get("/convenios/")
async def listar_convenios():
    return await Convenio.find_all().to_list()