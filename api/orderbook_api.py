# api/orderbook_api.py
from fastapi import APIRouter
from services.matching_engine import MatchingEngine

def create_orderbook_router(matching: MatchingEngine):
    router = APIRouter()

    @router.get("/orderbook/{symbol}")
    def get_orderbook(symbol: str):
        ob = matching.orderbook

        # bids / asks를 아래처럼 평탄화하여 응답
        bids = [
            {
                "price": o["price"],
                "qty": o["remaining_qty"],
            }
            for o in ob["bids"] if o["symbol"].upper() == symbol.upper()
        ]

        asks = [
            {
                "price": o["price"],
                "qty": o["remaining_qty"],
            }
            for o in ob["asks"] if o["symbol"].upper() == symbol.upper()
        ]

        return {"symbol": symbol, "bids": bids, "asks": asks}

    return router
