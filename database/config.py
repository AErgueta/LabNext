# Archivo: database/config.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os
from dotenv import load_dotenv

from models.estudio import Estudio
from models.orden import Orden
# 1. IMPORTAMOS LOS NUEVOS MODELOS
from models.medico import Medico
from models.convenio import Convenio
from models.usuario import Usuario # <-- 1. IMPORTAMOS EL USUARIO
from models.paciente import Paciente
from models.sede import Sede

load_dotenv()

async def conectar_bd():
    cadena_conexion = os.getenv("MONGO_URL")
    
    if not cadena_conexion:
        raise ValueError("No se encontró la cadena de conexión")

    client = AsyncIOMotorClient(cadena_conexion)
    
    # 2. LOS AGREGAMOS A LA LISTA
    await init_beanie(
        database=client.LabNext, 
        document_models=[Estudio, Orden, Medico, Convenio, Usuario, Paciente, Sede]
    )
    print("🚀 Base de datos conectada de forma segura")