# matching_http_server.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.db_matching import MatchingDB
from services.matching_engine import MatchingEngine

app = FastAPI()

db = MatchingDB(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", "myhts"),
    user=os.getenv("DB_USER", "myhts"),
    password=os.getenv("DB_PASSWORD", "myhts_pw"),
    port=int(os.getenv("DB_PORT", "5432")),
)
engine = MatchingEngine(db)

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    ok: bool
    user_id: int | None = None
    account_id: int | None = None


@app.post("/login", response_model=LoginResponse)
def login(req: LoginRequest):
    """
    간단 로그인 테스트용 엔드포인트.
    - users 테이블의 email/pw_hash 로 인증
    - 성공 시 user_id, primary_account_id 리턴
    """
    user_id, account_id = db.verify_user(req.email, req.password)
    if not user_id:
        # 401 Unauthorized
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return LoginResponse(ok=True, user_id=user_id, account_id=account_id)

class MatchRequest(BaseModel):
    symbol: str


@app.post("/match/symbol")
def match_symbol(req: MatchRequest):
    sym = req.symbol.upper()
    engine.match_symbol(sym)
    return {"ok": True, "symbol": sym}


@app.get("/health")
def health():
    return {"status": "ok"}
