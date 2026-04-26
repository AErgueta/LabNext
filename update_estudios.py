import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.estudio import Estudio 

load_dotenv()

async def migrar():
    mongo_url = os.getenv("MONGO_URL")
    client = AsyncIOMotorClient(mongo_url)
    
    # 1. Asegúrate que este sea el nombre de tu DB
    await init_beanie(database=client.LabNext, document_models=[Estudio])

    print("🚀 Iniciando migración masiva...")

    # 2. Usamos el operador $set de MongoDB directamente.
    # Esto busca todos los documentos que NO tengan el campo 'dias_demora'
    # y se los agrega de golpe con valor 1.
    resultado = await Estudio.find({"dias_demora": {"$exists": False}}).update({"$set": {"dias_demora": 2}})

    print(f"✅ Migración completada. Documentos actualizados: {resultado.modified_count}")

if __name__ == "__main__":
    asyncio.run(migrar())