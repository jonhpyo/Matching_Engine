from typing import List, Dict


class MatchingEngine:
    def __init__(self, order_repo, trade_repo, account_service):
        self.order_repo = order_repo
        self.trade_repo = trade_repo
        self.account_service = account_service

        # 메모리 오더북
        self.orderbook = {
            "bids": [],  # BUY
            "asks": [],  # SELL
        }

    # ---------------------------------------------------------
    # 지정가 주문
    # ---------------------------------------------------------
    def process_limit_order(self, order: dict):
        side = order["side"].upper()
        fills = []

        if side == "BUY":
            fills += self._match_order(order, self.orderbook["asks"])
            if order["remaining_qty"] > 0:
                self._add_to_orderbook(order, "bids")
        else:
            fills += self._match_order(order, self.orderbook["bids"])
            if order["remaining_qty"] > 0:
                self._add_to_orderbook(order, "asks")

        return fills

    # ---------------------------------------------------------
    # 시장가 주문
    # ---------------------------------------------------------
    def process_market_order(self, order: dict):
        side = order["side"].upper()

        if side == "BUY":
            self._match_order(order, self.orderbook["asks"], is_market=True)
        else:
            self._match_order(order, self.orderbook["bids"], is_market=True)

        # 시장가는 잔량 있으면 자동 취소
        if order["remaining_qty"] > 0:
            self.order_repo.update_order_remaining(
                order_id=order["id"],
                remaining_qty=0,
                status="CANCELLED"
            )

    # ---------------------------------------------------------
    # 핵심 매칭 로직
    # ---------------------------------------------------------
    def _match_order(self, incoming: dict, opposite_book: List[dict], is_market: bool = False):
        fills = []
        symbol = incoming["symbol"]
        side = incoming["side"].upper()

        i = 0
        while incoming["remaining_qty"] > 0 and i < len(opposite_book):

            top = opposite_book[i]

            # 지정가이면 가격 교차 조건 체크
            if not is_market:
                if side == "BUY" and incoming["price"] < top["price"]:
                    break
                if side == "SELL" and incoming["price"] > top["price"]:
                    break

            trade_qty = min(incoming["remaining_qty"], top["remaining_qty"])
            trade_price = top["price"]  # maker price

            # 체결 처리
            fill = self._execute_fill(
                buy=incoming if side == "BUY" else top,
                sell=top if side == "BUY" else incoming,
                price=trade_price,
                qty=trade_qty,
                symbol=symbol
            )
            fills.append(fill)

            # 잔량 감소
            incoming["remaining_qty"] -= trade_qty
            top["remaining_qty"] -= trade_qty

            if top["remaining_qty"] <= 0:
                opposite_book.pop(i)
            else:
                i += 1

        return fills

    # ---------------------------------------------------------
    # 체결 처리: DB + 계좌 + 주문상태
    # ---------------------------------------------------------
    def _execute_fill(self, buy, sell, price, qty, symbol):

        # --- BUY 체결 기록 ---
        self.trade_repo.insert_trade(
            user_id=buy["user_id"],
            account_id=buy["account_id"],
            symbol=symbol,
            side="BUY",
            price=price,
            qty=qty,
            order_id=buy["id"],
            exchange="LOCAL",
            remark=None,
        )

        # --- SELL 체결 기록 ---
        self.trade_repo.insert_trade(
            user_id=sell["user_id"],
            account_id=sell["account_id"],
            symbol=symbol,
            side="SELL",
            price=price,
            qty=qty,
            order_id=sell["id"],
            exchange="LOCAL",
            remark=None,
        )

        # --- 계좌 반영 ---
        self.account_service.apply_fill(
            user_id=buy["user_id"],
            account_id=buy["account_id"],
            symbol=symbol,
            side="BUY",
            price=price,
            qty=qty
        )
        self.account_service.apply_fill(
            user_id=sell["user_id"],
            account_id=sell["account_id"],
            symbol=symbol,
            side="SELL",
            price=price,
            qty=qty
        )

        # --- 주문 상태 업데이트 ---
        self._update_order_status(buy)
        self._update_order_status(sell)

        # UI 에 전달할 fill 구조
        return {
            "symbol": symbol,
            "price": price,
            "qty": qty,
            "buy_order_id": buy["id"],
            "sell_order_id": sell["id"],
        }

    # ---------------------------------------------------------
    # 주문상태 업데이트
    # ---------------------------------------------------------
    def _update_order_status(self, order):
        remaining = order["remaining_qty"]
        status = "FILLED" if remaining <= 0 else "PARTIAL"

        self.order_repo.update_order_remaining(
            order_id=order["id"],
            remaining_qty=max(remaining, 0),
            status=status
        )

    # ---------------------------------------------------------
    # 오더북 등록
    # ---------------------------------------------------------
    def _add_to_orderbook(self, order, side: str):
        self.orderbook[side].append(order)

        if side == "bids":   # DESC
            self.orderbook[side].sort(key=lambda x: (-x["price"], x["id"]))
        else:                # ASC
            self.orderbook[side].sort(key=lambda x: (x["price"], x["id"]))
