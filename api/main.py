# api/main.py
import os

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
import jwt
from api.auth import get_current_user, UserInfo
from services.db_login import LoginDB
from fastapi import status
from datetime import datetime, timedelta

from services.db_matching import MatchingDB

ENGINE_URL = os.getenv("ENGINE_URL", "http://engine:9000")
SECRET = "MYHTS_SECRET_KEY"

app = FastAPI(
    title="HTS API Server",
    description="클라이언트(HTS)에서 직접 호출하는 API 서버",
    version="1.0.0",
)

db = LoginDB(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", "myhts"),
    user=os.getenv("DB_USER", "myhts"),
    password=os.getenv("DB_PASSWORD", "myhts_pw"),
    port=int(os.getenv("DB_PORT", "5432")),
)

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginReq(BaseModel):
    email: str
    password: str

class LoginRes(BaseModel):
    ok: bool
    user_id: int | None = None
    account_id: int | None = None
    current_user: str | None = None

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    # auto_open_account: bool = True
    # account_name: str | None = None

class SignupResponse(BaseModel):
    user_id: int
    email: EmailStr
    # account_no: str | None = None

class CreateAccountRequest(BaseModel):
    account_name: str | None = None

class CreateAccountResponse(BaseModel):
    user_id: int
    account_no: str
    account_name: str

class TradeItem(BaseModel):
    account_no: str
    symbol: str
    side: str
    price: float
    quantity: float
    trade_time: datetime
    remark: str | None = None


@app.get("/health")
def health():
    return {"status": "api ok"}


@app.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    사용자 로그인:
    - form.username
    - form.password
    """
    user = db.verify_user(form.username, form.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = user
    current_user = form.username

    payload = {
        "user_id": user_id,
        "email": current_user,
        "exp": datetime.utcnow() + timedelta(hours=12)
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return Token(access_token=token, token_type="bearer")

@app.get("/me")
def read_me(current_user: int = Depends(get_current_user)):
    return {"email": current_user}

@app.post("/signup", response_model=SignupResponse)
def signup(req: SignupRequest):
    """
    회원가입 + (옵션) 기본 계좌 하나 자동 개설
    """
    # 1) 이미 존재하는 이메일인지 검사
    existing_id = db.get_user_id_by_email(req.email)
    if existing_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입된 이메일입니다.",
        )

    # 2) users INSERT
    ok = db.insert_user(req.email, req.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 실패",
        )

    # 3) 새 user_id 다시 조회
    user_id = db.get_user_id_by_email(req.email)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원정보 조회 실패",
        )

    # 4) 자동 계좌 개설 옵션
    # account_no: str | None = None
    # if req.auto_open_account:
    #     name = req.account_name or "기본계좌"
    #     account_no = db.create_account(user_id, name=name)
    #     if account_no is None:
    #         # 계좌 개설 실패는 일단 경고만 띄우고 회원가입 자체는 성공으로 간주
    #         print(f"[signup] user_id={user_id} 계좌 개설 실패")

    return SignupResponse(
        user_id=user_id,
        email=req.email
        # account_no=account_no
    )


@app.post("/accounts/create", response_model=CreateAccountResponse)
def create_account(
    req: CreateAccountRequest,
    user_id=Depends(get_current_user)
):
    db = LoginDB()
    account_name = req.account_name or ""

    account_no = db.create_account(user_id, account_name)
    if not account_no:
        raise HTTPException(
            status_code=500, detail="계좌 개설에 실패했습니다."
        )

    return CreateAccountResponse(
        user_id=user_id,
        account_no=account_no,
        account_name=account_name
    )

@app.get("/trades/my", response_model=list[TradeItem])
def get_my_trades(
    limit: int = 100,
    user_id=Depends(get_current_user)
):
    try:
        match_db = MatchingDB()
        rows = match_db.get_trades_by_user(user_id, limit=limit)

        return [
            TradeItem(
                account_no=r["account_no"],
                symbol=r["symbol"],
                side=r["side"],
                price=float(r["price"]),
                quantity=float(r["quantity"]),
                trade_time=r["trade_time"],
                remark=r["remark"],
            )
            for r in rows
        ]
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Trade 조회 실패")

# @app.post("/order/limit-buy")
# def limit_buy(order: Order, user_id: int = Depends(get_current_user)):
#     # user_id = JWT에서 가져온 값
#     return engine.submit_order(user_id, order)