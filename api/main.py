# api/main.py
import os

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
import jwt

from api.account_api import create_account_router
from api.auth_api import get_current_user
from api.trade_api import create_trade_router
from api.orderbook_api import create_orderbook_router

from repositories.account_repository import AccountRepository
from repositories.order_repository import OrderRepository
from repositories.trade_repositories import TradeRepository

from services.account_service import AccountService
from services.trade_service import TradeService
from services.db_login import LoginDB
from services.db_matching import MatchingDB
from services.matching_engine import MatchingEngine
from services.marketdata_service import MarketDataService   # ★ 여기 중요!

from fastapi import status
from datetime import datetime, timedelta


SECRET = "MYHTS_SECRET_KEY"


# ----------------------------------------------------------
# FastAPI 기본 설정
# ----------------------------------------------------------
app = FastAPI(
    title="HTS API Server",
    description="HTS 클라이언트가 직접 호출하는 API 서버",
    version="1.0.0",
)


# ----------------------------------------------------------
# DB 연결
# ----------------------------------------------------------
db = LoginDB(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", "myhts"),
    user=os.getenv("DB_USER", "myhts"),
    password=os.getenv("DB_PASSWORD", "myhts_pw"),
    port=int(os.getenv("DB_PORT", "5432")),
)

matchingDb = MatchingDB()
conn = matchingDb.conn

order_repo = OrderRepository(conn)
trade_repo = TradeRepository(conn)
account_repo = AccountRepository(conn)

account_service = AccountService(account_repo)
trade_service = TradeService(trade_repo)


# ----------------------------------------------------------
# 매칭엔진 & Binance Service 준비
# ----------------------------------------------------------
matching_engine = MatchingEngine(order_repo, trade_repo, account_service)

binance_service = MarketDataService(
    symbol="SOLUSDT",
    limit=20
)


# ----------------------------------------------------------
# 라우터 등록
# ----------------------------------------------------------
app.include_router(create_orderbook_router(matching_engine, order_repo))
app.include_router(create_trade_router(trade_repo, trade_service))
app.include_router(create_account_router(account_repo, account_service))


# ----------------------------------------------------------
# Pydantic 모델
# ----------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class SignupResponse(BaseModel):
    user_id: int
    email: EmailStr


# ----------------------------------------------------------
# 기본 엔드포인트
# ----------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "api ok"}


@app.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = db.verify_user(form.username, form.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "user_id": user,
        "email": form.username,
        "exp": datetime.utcnow() + timedelta(hours=12)
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return Token(access_token=token, token_type="bearer")


@app.post("/signup", response_model=SignupResponse)
def signup(req: SignupRequest):
    existing_id = db.get_user_id_by_email(req.email)
    if existing_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입된 이메일입니다.",
        )

    ok = db.insert_user(req.email, req.password)
    if not ok:
        raise HTTPException(status_code=500, detail="회원가입 실패")

    user_id = db.get_user_id_by_email(req.email)

    return SignupResponse(user_id=user_id, email=req.email)
