# Archivo: utils/seguridad.py
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración secreta
#SECRET_KEY = "mi_clave_super_secreta_labnext01"
#ALGORITHM = "HS256"
#ACCESS_TOKEN_EXPIRE_MINUTES = 120 

# Configuración secreta (ahora jala los datos del .env)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))

# Herramientas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Le decimos al guardia que la puerta donde dan las llaves es "/login"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def encriptar_password(password: str) -> str:
    return pwd_context.hash(password)

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def crear_token_acceso(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- NUESTRO GUARDIA DE SEGURIDAD NORMAL ---
def verificar_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        rol: str = payload.get("rol")  # <-- NUEVO: El guardia ahora lee el rol
        
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
            
        # NUEVO: Ahora el guardia nos devuelve un paquete con los datos del usuario
        return {"username": username, "rol": rol} 
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La sesión ha expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

# --- NUEVO: EL GUARDIA DE ÉLITE (SOLO PARA ADMINISTRADORES) ---
def verificar_admin(usuario_actual: dict = Depends(verificar_token)):
    # Este guardia revisa el paquete. Si el rol no es "admin", te saca a patadas.
    if usuario_actual.get("rol") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permisos insuficientes. Esta acción requiere rol de Administrador."
        )
    return usuario_actual