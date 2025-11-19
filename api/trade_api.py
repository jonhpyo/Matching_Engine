# api/trade_api.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.auth_api import get_current_user
from services.trade_service import TradeService
from repositories.trade_repositories import TradeRepository


def create_trade_router(trade_repo: TradeRepository, trade_service: TradeService):
    router = APIRouter()

    # ----------------------------
    # Pydantic 모델
    # ----------------------------
    class TradeIn(BaseModel):
        user_id: int
        account_id: int
        symbol: str
        side: str
        price: float
        qty: float
        order_id: int | None = None
        exchange: str | None = None
        remark: str | None = None

    # ----------------------------
    # 1) 체결 INSERT
    # ----------------------------
    @router.post("/trades/insert")
    def insert_trade(trade: TradeIn):
        ok = trade_service.insert_trade(**trade.dict())
        return {"success": ok}

    # ----------------------------
    # 2) 내 체결 조회
    # ----------------------------
    @router.get("/trades/my")
    def get_my_trades(limit: int = 100, current_user=Depends(get_current_user)):
        user_id = current_user.user_id
        return trade_repo.get_trades_by_user(user_id, limit)

    return router
