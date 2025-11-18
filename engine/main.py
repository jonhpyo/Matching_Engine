# engine/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from matching_http_server import engine  # 전역 MatchingEngine 인스턴스


class Order(BaseModel):
    user_id: str
    symbol: str
    side: str
    price: float
    qty: float
    order_type: Optional[str] = "LIMIT"


app = FastAPI(
    title="Matching Engine Server",
    description="실제 주문 매칭 로직이 돌아가는 내부 서버",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "engine ok"}


@app.post("/order")
def process_order(order: Order):
    """
    API 서버에서 넘어온 주문을 매칭엔진에 전달
    """
    result = engine.submit_order(order)
    return result
