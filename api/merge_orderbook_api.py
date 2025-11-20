# api/merge_orderbook_api.py
from fastapi import APIRouter
from services.matching_engine import MatchingEngine
from repositories.order_repository import OrderRepository
from services.binance_depth import BinanceDepthService


def create_merged_orderbook_router(
        matching: MatchingEngine,
        order_repo: OrderRepository,
        binance: BinanceDepthService,
    ):
    router = APIRouter()

    @router.get("/orderbook/merged")
    def get_merged_orderbook(symbol: str):

        symbol = symbol.upper()

        # 1) 실시간 binance depth 가져오기
        b = binance.get_depth(symbol)
        if not b:
            b = {"bids": [], "asks": [], "mid": 0}

        # 2) local DB 오더북 가져오기
        db = order_repo.get_grouped_orderbook(symbol)

        bids_map = {}
        asks_map = {}

        # Binance 가격 레벨 기반 테이블 생성
        for price, qty in b["bids"]:
            bids_map[float(price)] = {"price": float(price), "binance_qty": float(qty), "db_qty": 0, "cnt": 0}

        for price, qty in b["asks"]:
            asks_map[float(price)] = {"price": float(price), "binance_qty": float(qty), "db_qty": 0, "cnt": 0}

        # DB 잔량 매핑
        for row in db:
            px = float(row["price"])
            qty = float(row["qty"])
            cnt = int(row["cnt"])

            if row["side"] == "BUY":
                if px not in bids_map:
                    bids_map[px] = {"price": px, "binance_qty": 0, "db_qty": qty, "cnt": cnt}
                else:
                    bids_map[px]["db_qty"] = qty
                    bids_map[px]["cnt"] = cnt
            else:
                if px not in asks_map:
                    asks_map[px] = {"price": px, "binance_qty": 0, "db_qty": qty, "cnt": cnt}
                else:
                    asks_map[px]["db_qty"] = qty
                    asks_map[px]["cnt"] = cnt

        bids = sorted(bids_map.values(), key=lambda x: -x["price"])
        asks = sorted(asks_map.values(), key=lambda x: x["price"])

        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "mid": b.get("mid", 0)
        }

    return router
