# services/order_service.py

class OrderService:
    """
    OrderService (V2)
    -----------------------
    - OrderRepository + TradeRepository + MatchingEngine
    - 지정가/시장가 주문 처리
    - 주문 INSERT → 매칭 → 체결 저장 → 잔량 업데이트
    """

    def __init__(self, order_repo, trade_repo, matching_engine):
        self.order_repo = order_repo
        self.trade_repo = trade_repo
        self.engine = matching_engine

    # ---------------------------------------------------------
    # 단순 주문 INSERT (UI에서 사용)
    # ---------------------------------------------------------
    def place_order(self, user_id, account_id, symbol, side, price, qty):
        """
        DB에 WORKING 상태로 주문을 삽입하고 order_id 를 반환
        """
        return self.order_repo.insert_order(
            user_id=user_id,
            account_id=account_id,
            symbol=symbol,
            side=side.upper(),
            price=price,
            quantity=qty,
            remaining_qty=qty,
            status="WORKING",
        )

    # ---------------------------------------------------------
    # 지정가 주문
    # ---------------------------------------------------------
    def place_limit(self, user_id, account_id, symbol, side, price, qty):
        """
        1) DB INSERT
        2) 매칭엔진에 전달
        3) 체결 결과 반환
        """
        order_id = self.place_order(
            user_id=user_id,
            account_id=account_id,
            symbol=symbol,
            side=side,
            price=price,
            qty=qty
        )

        if not order_id:
            return {"order_id": None, "fills": []}

        # MatchingEngine은 DB에서 주문 읽어야 하므로 order_repo.get_order 필요
        order = self.order_repo.get_order(order_id)
        if not order:
            return {"order_id": order_id, "fills": []}

        # 매칭엔진 호출
        fills = self.engine.process_limit_order(order)

        return {"order_id": order_id, "fills": fills}

    # ---------------------------------------------------------
    # 시장가 주문
    # ---------------------------------------------------------
    def place_market(self, user_id, account_id, symbol, side, qty):
        order_id = self.place_order(
            user_id=user_id,
            account_id=account_id,
            symbol=symbol,
            side=side,
            price=0.0,
            qty=qty
        )

        if not order_id:
            return {"order_id": None, "fills": []}

        order = self.order_repo.get_order(order_id)
        if not order:
            return {"order_id": order_id, "fills": []}

        fills = self.engine.process_market_order(order)

        return {"order_id": order_id, "fills": fills}

    # ---------------------------------------------------------
    # 잔량 업데이트
    # ---------------------------------------------------------
    def update_remaining(self, order_id, remaining_qty, status=None):
        return self.order_repo.update_order_remaining(order_id, remaining_qty, status)

    # ---------------------------------------------------------
    # 주문 취소
    # ---------------------------------------------------------
    def cancel_orders(self, order_ids):
        return self.order_repo.cancel_orders(order_ids)

    # ---------------------------------------------------------
    # 미체결 조회
    # ---------------------------------------------------------
    def get_user_working_orders(self, user_id, limit=100):
        return self.order_repo.get_working_orders_by_user(user_id, limit)
