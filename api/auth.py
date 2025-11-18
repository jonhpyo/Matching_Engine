
# api/auth.py
import os
from fastapi import Header, HTTPException
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from services.db_login import LoginDB
SECRET = "MYHTS_SECRET_KEY"
ALGORITHM = "HS256"

# ---------------------------
#  UserInfo 모델 (HTS/서버 공용)
# ---------------------------
class UserInfo(BaseModel):
    user_id: int
    email: str

db = LoginDB(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", "myhts"),
    user=os.getenv("DB_USER", "myhts"),
    password=os.getenv("DB_PASSWORD", "myhts_pw"),
    port=int(os.getenv("DB_PORT", "5432")),
)

def get_current_user(Authorization: str = Header(None)):
    if not Authorization:
        raise HTTPException(401, "Missing Authorization header")

    try:
        scheme, token = Authorization.split()
    except:
        raise HTTPException(401, "Invalid Authorization header")

    if scheme.lower() != "bearer":
        raise HTTPException(401, "Invalid token scheme (must be Bearer)")

    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        return payload["user_id"]   # user_id
        #return payload["sub"]  # user_id
    except Exception:
        raise HTTPException(401, "Invalid or expired token")



def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=1)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)