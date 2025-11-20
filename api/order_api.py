# api/orderbook_api.py
from fastapi import APIRouter, HTTPException
from services.matching_engine import MatchingEngine
from repositories.order_repository import OrderRepository
from services.marketdata_service import MarketDataService


def create_orderbook_router(
        matching: MatchingEngine,
        order_repo: OrderRepository,
        md: MarketDataService
):
    """
    /orderbook            → 매칭엔진 메모리 오더북
    /orderbook/local      → DB 기반 오더북
    /orderbook/binance    → Binance 실시간 depth
    /orderbook/merged     → Binance 가격 + DB qty/cnt 합침
    """

    router = APIRouter()

    # ----------------------------------------------------------
    # 1) 매칭엔진 메모리 기반 (/orderbook)
    # ----------------------------------------------------------
    @router.get("/orderbook")
    def get_engine_orderbook(symbol: str):
        try:
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

            return {
                "bids": sorted(
                    [{"price": p, **v} for p, v in bids.items()],
                    key=lambda x: -x["price"]
                ),
                "asks": sorted(
                    [{"price": p, **v} for p, v in asks.items()],
                    key=lambda x: x["price"]
                ),
            }

        except Exception as e:
            print("[OrderBookAPI] /orderbook ERROR:", e)
            raise HTTPException(500, "Engine orderbook failed")

    # ----------------------------------------------------------
    # 2) DB 기반 (/orderbook/local)
    # ----------------------------------------------------------
    @router.get("/orderbook/local")
    def get_local_orderbook(symbol: str):
        try:
            symbol = symbol.upper()
            rows = order_repo.get_grouped_orderbook(symbol)

            bids = []
            asks = []

            for r in rows:
                px = float(r["price"])
                qty = float(r["qty"])
                cnt = int(r["cnt"])

                entry = {"price": px, "qty": qty, "cnt": cnt}

                if r["side"].upper() == "BUY":
                    bids.append(entry)
                else:
                    asks.append(entry)

            return {
                "bids": sorted(bids, key=lambda x: -x["price"]),
                "asks": sorted(asks, key=lambda x: x["price"]),
            }

        except Exception as e:
            print("[OrderBookAPI] /orderbook/local ERROR:", e)
            raise HTTPException(500, "Local orderbook failed")

    # ----------------------------------------------------------
    # 3) Binance Depth (/orderbook/binance)
    # ----------------------------------------------------------
    @router.get("/orderbook/binance")
    def get_binance_depth(symbol: str):
        try:
            symbol = symbol.upper()
            md.set_symbol(symbol)
            snap = md.fetch_depth()

            if snap is None:
                raise RuntimeError("snap is None")

            bids = [{"price": p, "qty": q, "cnt": 0} for p, q, _ in snap.bids]
            asks = [{"price": p, "qty": q, "cnt": 0} for p, q, _ in snap.asks]

            return {
                "symbol": symbol,
                "bids": bids,
                "asks": asks,
                "mid": snap.mid,
            }

        except Exception as e:
            print("[OrderBookAPI] /orderbook/binance ERROR:", e)
            raise HTTPException(500, "Binance depth failed")

    # ----------------------------------------------------------
    # 4) Binance + DB merged (/orderbook/merged)
    # ----------------------------------------------------------
    @router.get("/orderbook/merged")
    def get_merged(symbol: str):
        try:
            symbol = symbol.upper()
            md.set_symbol(symbol)

            # Binance depth
            snap = md.fetch_depth()
            if snap is None:
                raise RuntimeError("snap is None")

            # Local DB
            local = order_repo.get_grouped_orderbook(symbol)

            local_bids = {}
            local_asks = {}

            for r in local:
                px = float(r["price"])
                local_entry = {"qty": float(r["qty"]), "cnt": int(r["cnt"])}

                if r["side"].upper() == "BUY":
                    local_bids[px] = local_entry
                else:
                    local_asks[px] = local_entry

            # merge
            bids = []
            for price, q, _ in snap.bids:
                o = local_bids.get(price, {"qty": 0, "cnt": 0})
                bids.append({"price": price, "qty": o["qty"], "cnt": o["cnt"]})

            asks = []
            for price, q, _ in snap.asks:
                o = local_asks.get(price, {"qty": 0, "cnt": 0})
                asks.append({"price": price, "qty": o["qty"], "cnt": o["cnt"]})

            return {
                "symbol": symbol,
                "bids": bids,
                "asks": asks,
                "mid": snap.mid,
            }

        except Exception as e:
            print("[OrderBookAPI] /orderbook/merged ERROR:", e)
            raise HTTPException(500, "Merged orderbook failed")

    return router
