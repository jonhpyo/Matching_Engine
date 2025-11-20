# api/orderbook_api.py
from fastapi import APIRouter
from services.matching_engine import MatchingEngine
from repositories.order_repository import OrderRepository


def create_orderbook_router(matching: MatchingEngine, order_repo: OrderRepository):
    """
    /orderbook          → 매칭엔진(MEMORY orderbook)
    /orderbook/local    → DB 기반(order 테이블) qty/cnt 집계
    """
    router = APIRouter()

    # ----------------------------------------------------------
    # 1) 메모리 기반 오더북 (Matching Engine)
    # ----------------------------------------------------------
    @router.get("/orderbook")
    def get_orderbook(symbol: str):
        symbol = symbol.upper()
        ob = matching.orderbook

        result = {"bids": [], "asks": []}

        def group_book(book):
            grouped = {}
            for o in book:
                if o["symbol"].upper() != symbol:
                    continue
                px = o["price"]
                if px not in grouped:
                    grouped[px] = {"qty": 0, "cnt": 0}
                grouped[px]["qty"] += o["remaining_qty"]
                grouped[px]["cnt"] += 1
            return grouped

        bids = group_book(ob["bids"])
        asks = group_book(ob["asks"])

        result["bids"] = sorted(
            [{"price": p, **v} for p, v in bids.items()],
            key=lambda x: -x["price"]
        )
        result["asks"] = sorted(
            [{"price": p, **v} for p, v in asks.items()],
            key=lambda x: x["price"]
        )

        return result

    # ----------------------------------------------------------
    # 2) DB 기반 오더북 (order 테이블)
    # ----------------------------------------------------------
    @router.get("/orderbook/local")
    def get_local_orderbook(symbol: str):
        symbol = symbol.upper()
        rows = order_repo.get_grouped_orderbook(symbol)

        bids = []
        asks = []

        for r in rows:
            side = r["side"].upper()
            px = float(r["price"])
            qty = float(r["qty"])
            cnt = int(r["cnt"])

            entry = {"price": px, "qty": qty, "cnt": cnt}

            if side == "BUY":
                bids.append(entry)
            else:
                asks.append(entry)

        bids.sort(key=lambda x: -x["price"])
        asks.sort(key=lambda x: x["price"])

        return {"bids": bids, "asks": asks}

    return router
