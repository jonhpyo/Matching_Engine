# api/auth_api.py
import os
from fastapi import Header, HTTPException
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from services.db_login import LoginDB

SECRET = "MYHTS_SECRET_KEY"
ALGORITHM = "HS256"

# ---------------------------
# UserInfo 모델 (HTS/서버 공용)
# ---------------------------
class UserInfo(BaseModel):
    user_id: int
    email: str


# ---------------------------
# 단일 DB 인스턴스 (중복 방지)
# ---------------------------
db = LoginDB(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", "myhts"),
    user=os.getenv("DB_USER", "myhts"),
    password=os.getenv("DB_PASSWORD", "myhts_pw"),
    port=int(os.getenv("DB_PORT", "5432")),
)


# ---------------------------------------------------
# 현재 사용자 정보 추출
# ---------------------------------------------------
def get_current_user(Authorization: str = Header(None)) -> UserInfo:
    if not Authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        scheme, token = Authorization.split()
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token scheme (must be Bearer)")

    # JWT 해석
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        user_info = UserInfo(
            user_id=payload["user_id"],
            email=payload["email"]
        )
        return user_info
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------
# 토큰 생성
# ---------------------------------------------------
def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=1)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET, algorithm=ALGORITHM)
