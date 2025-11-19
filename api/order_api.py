# api/order_api.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.auth_api import get_current_user
from services.order_service import OrderService


class LimitOrderIn(BaseModel):
    user_id: int
    account_id: int
    symbol: str
    side: str
    price: float
    qty: float


class MarketOrderIn(BaseModel):
    user_id: int
    account_id: int
    symbol: str
    side: str
    qty: float


class CancelIn(BaseModel):
    order_ids: list[int]


def create_order_router(order_repo, trade_repo, matching_engine):
    router = APIRouter()
    service = OrderService(order_repo, trade_repo, matching_engine)

    # -----------------------------
    # 지정가 주문
    # -----------------------------
    @router.post("/orders/limit")
    def place_limit(order: LimitOrderIn, user=Depends(get_current_user)):
        if user.user_id != order.user_id:
            raise HTTPException(403, "User ID mismatch")

        return service.place_limit(**order.dict())

    # -----------------------------
    # 시장가 주문
    # -----------------------------
    @router.post("/orders/market")
    def place_market(order: MarketOrderIn, user=Depends(get_current_user)):
        if user.user_id != order.user_id:
            raise HTTPException(403, "User ID mismatch")

        return service.place_market(**order.dict())

    # -----------------------------
    # 미체결 주문 조회
    # -----------------------------
    @router.get("/orders/working")
    def get_working(user_id: int, limit: int = 100):
        return service.get_user_working_orders(user_id, limit)

    # -----------------------------
    # 주문 취소
    # -----------------------------
    @router.post("/orders/cancel")
    def cancel_orders(body: CancelIn, user=Depends(get_current_user)):
        return service.cancel_orders(body.order_ids)

    return router
