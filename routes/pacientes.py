from fastapi import APIRouter, Depends, HTTPException, status
from models.paciente import Paciente
from utils.seguridad import verificar_token, verificar_admin
from typing import List

router = APIRouter()

# --- 1. REGISTRAR PACIENTE ---
# Tanto María como Alfonso pueden registrar pacientes
@router.post("/pacientes", status_code=status.HTTP_201_CREATED)
async def registrar_paciente(paciente: Paciente, usuario: dict = Depends(verificar_token)):
    # Verificamos si el CI ya existe en la base de datos
    existe = await Paciente.find_one(Paciente.ci == paciente.ci)
    if existe:
        raise HTTPException(
            status_code=400, 
            detail=f"El paciente con CI {paciente.ci} ya está registrado como {existe.nombre_completo}"
        )
    
    await paciente.insert()
    return {"status": "success", "message": f"Paciente {paciente.nombre_completo} registrado correctamente"}

# 1. Ruta para listar TODOS los pacientes (Bypass de seguridad activado)
@router.get("/pacientes")
async def listar_pacientes():
    return await Paciente.find_all().to_list()


# 2. Ruta para buscar UN paciente específico por su CI (Bypass de seguridad activado)
@router.get("/pacientes/{ci}")
async def obtener_paciente(ci: str):
    paciente = await Paciente.find_one(Paciente.ci == ci)
    
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
    return paciente

# --- 4. ACTUALIZAR DATOS ---
# Si el paciente cambió de teléfono o de seguro
@router.put("/pacientes/{ci}")
async def actualizar_paciente(ci: str, datos_actualizados: Paciente, usuario: dict = Depends(verificar_token)):
    paciente = await Paciente.find_one(Paciente.ci == ci)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Actualizamos los campos (excepto el CI que es único e inmutable)
    await paciente.update({"$set": datos_actualizados.dict(exclude={"ci", "id", "fecha_registro"})})
    return {"message": "Datos del paciente actualizados"}

# --- 5. ELIMINAR PACIENTE (SOLO ADMIN) ---
# María no puede borrar pacientes, solo tú puedes hacerlo
@router.delete("/pacientes/{ci}")
async def eliminar_paciente(ci: str, usuario: dict = Depends(verificar_admin)):
    paciente = await Paciente.find_one(Paciente.ci == ci)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    await paciente.delete()
    return {"message": f"Ficha del paciente {ci} eliminada del sistema"}