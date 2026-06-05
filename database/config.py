# Archivo: database/config.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os
from dotenv import load_dotenv

from models.estudio import Estudio
from models.orden import Orden
from models.medico import Medico
from models.convenio import Convenio
from models.usuario import Usuario 
from models.paciente import Paciente
from models.sede import Sede
from models.flujo_muestra import FlujoMuestra
from models.muestra import Muestra
from models.resultado import ResultadoMuestra
from models.log_envios import LogEnvio # <--- 1. IMPORTA EL NUEVO MODELO AQUÍ

load_dotenv()

async def conectar_bd():
    cadena_conexion = os.getenv("MONGO_URL")
    
    if not cadena_conexion:
        raise ValueError("No se encontró la cadena de conexión")

    client = AsyncIOMotorClient(cadena_conexion)
    
    # 2. AGRÉGALO A LA LISTA DE ABAJO
    await init_beanie(
        database=client.LabNext, 
        document_models=[
            Estudio, 
            Orden, 
            Medico, 
            Convenio, 
            Usuario, 
            Paciente, 
            Sede, 
            FlujoMuestra, 
            Muestra, 
            ResultadoMuestra,
            LogEnvio # <--- 2. AÑÁDELO AQUÍ AL FINAL
        ]
    )
    print("🚀 Base de datos conectada de forma segura")