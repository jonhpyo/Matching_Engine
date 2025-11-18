# services/matching_engine.py
from services.db_matching import MatchingDB


class MatchingEngine:
    """
    MatchingDB 를 이용해 orders / trades / accounts / positions 를
    전부 DB 안에서 처리하는 매칭 엔진.
    """

    def __init__(self, db: MatchingDB):
        self.db = db

    def match_symbol(self, symbol: str):
        symbol = symbol.upper()

        try:
            orders = self.db.fetch_working_orders(symbol)
            buys  = [o for o in orders if o["side"] == "BUY"]
            sells = [o for o in orders if o["side"] == "SELL"]

            if not buys or not sells:
                return

            # 가격 기준 정렬 (BUY: 높은 가격 우선, SELL: 낮은 가격 우선)
            buys.sort(key=lambda o: (-float(o["price"]), o["created_at"]))
            sells.sort(key=lambda o: (float(o["price"]), o["created_at"]))

            trades = []

            while buys and sells and buys[0]["price"] >= sells[0]["price"]:
                buy = buys[0]
                sell = sells[0]

                qty = min(float(buy["remaining_qty"]), float(sell["remaining_qty"]))
                price = float(buy["price"] + sell["price"]) / 2.0

                trades.append((buy, sell, price, qty))

                buy["remaining_qty"]  = float(buy["remaining_qty"])  - qty
                sell["remaining_qty"] = float(sell["remaining_qty"]) - qty

                if buy["remaining_qty"] <= 0:
                    buys.pop(0)
                if sell["remaining_qty"] <= 0:
                    sells.pop(0)

            # DB 반영
            for buy, sell, price, qty in trades:
                # 1) 체결 기록
                self.db.insert_trade_record(buy, sell, symbol, price, qty)

                # 2) 주문 상태/잔량
                for o in (buy, sell):
                    status = "FILLED" if o["remaining_qty"] <= 0 else "PARTIAL"
                    self.db.update_order(o["id"], o["remaining_qty"], status)

                # 3) 계좌 잔고
                notional = price * qty
                self.db.update_account_balance(buy["account_id"], -notional)
                self.db.update_account_balance(sell["account_id"], +notional)

                # 4) 포지션
                self.db.update_position_on_trade(
                    account_id=buy["account_id"],
                    user_id=buy["user_id"],
                    symbol=symbol,
                    side="BUY",
                    price=price,
                    qty=qty,
                )
                self.db.update_position_on_trade(
                    account_id=sell["account_id"],
                    user_id=sell["user_id"],
                    symbol=symbol,
                    side="SELL",
                    price=price,
                    qty=qty,
                )

            self.db.commit()
            print(f"[MatchingEngine] {symbol} trades={len(trades)}")

        except Exception as e:
            self.db.rollback()
            print(f"[MatchingEngine] match_symbol({symbol}) error:", e)
