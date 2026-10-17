import asyncio
import os
import bcrypt
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def resetear_clave():
    NUEVA_CONTRASEÑA = "admin123"
    
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        print("❌ Error: No se encontró MONGO_URL en el archivo .env")
        return

    client = AsyncIOMotorClient(mongo_url)
    
    # Nombre exacto de tu base de datos
    db = client["LabNext"]
    
    # Generar hash con bcrypt
    salt = bcrypt.gensalt()
    nuevo_hash = bcrypt.hashpw(NUEVA_CONTRASEÑA.encode('utf-8'), salt).decode('utf-8')
    
    # Colecciones a actualizar (incluyendo la oficial 'usuarios_sistema')
    colecciones = ["usuarios_sistema", "Usuario", "usuarios"]
    
    actualizado = False
    for nombre_col in colecciones:
        coll = db[nombre_col]
        res = await coll.update_many(
            {"username": "alfonso_admin"},
            {"$set": {"password_hash": nuevo_hash}}
        )
        if res.matched_count > 0:
            print(f"🎯 Contraseña actualizada en la colección '{nombre_col}' (Coincidencias: {res.matched_count})")
            actualizado = True

    if actualizado:
        print("\n=========================================")
        print("✅ ¡Contraseña reseteada con éxito!")
        print("👤 Usuario: alfonso_admin")
        print(f"🔑 Nueva Contraseña: {NUEVA_CONTRASEÑA}")
        print("=========================================\n")
    else:
        print("❌ No se encontró ningún usuario 'alfonso_admin'.")

if __name__ == "__main__":
    asyncio.run(resetear_clave())