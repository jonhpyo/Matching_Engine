from fastapi import APIRouter
from services.matching_engine import MatchingEngine
from repositories.order_repository import OrderRepository
import requests

def create_binance_orderbook_router(matching: MatchingEngine, order_repo: OrderRepository):
    router = APIRouter()

    @router.get("/orderbook/merged")
    def get_merged_orderbook(symbol: str):
        symbol = symbol.upper()

        # 1) Binance Depth 가져오기
        url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"
        r = requests.get(url)
        if r.status_code != 200:
            return {"bids": [], "asks": []}
        data = r.json()

        binance_bids = [(float(p), float(q)) for p, q in data.get("bids", [])]
        binance_asks = [(float(p), float(q)) for p, q in data.get("asks", [])]

        # 2) DB 집계
        db_rows = order_repo.bucket_by_price(symbol)
        db_map = {}  # price → {qty, cnt, side}

        for r in db_rows:
            price = float(r["price"])
            side = r["side"]
            qty = float(r["qty"])
            cnt = int(r["cnt"])

            db_map[(side, price)] = {"qty": qty, "cnt": cnt}

        # 3) Merge → Binance price 기준으로 Local qty/cnt 붙이기
        merged_bids = []
        for price, _ in binance_bids:
            key = ("BUY", price)
            qty = db_map.get(key, {}).get("qty", 0.0)
            cnt = db_map.get(key, {}).get("cnt", 0)
            merged_bids.append({
                "price": price,
                "qty": qty,
                "cnt": cnt
            })

        merged_asks = []
        for price, _ in binance_asks:
            key = ("SELL", price)
            qty = db_map.get(key, {}).get("qty", 0.0)
            cnt = db_map.get(key, {}).get("cnt", 0)
            merged_asks.append({
                "price": price,
                "qty": qty,
                "cnt": cnt
            })

        return {
            "bids": merged_bids,
            "asks": merged_asks
        }

    return router
