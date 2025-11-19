# services/account_service.py

class AccountService:
    def __init__(self, account_repo):
        self.acc_repo = account_repo

    # -----------------------------------
    # 기본 계좌 조회
    # -----------------------------------
    def get_primary_account(self, user_id: int):
        return self.acc_repo.get_primary_account_id(user_id)

    # -----------------------------------
    # 체결 후 계좌/포지션 업데이트
    # -----------------------------------
    def apply_fill(self, user_id: int, account_id: int,
                   symbol: str, side: str, price: float, qty: float):

        summary = self.acc_repo.get_account_summary(account_id)
        balance = summary["balance"]
        trade_value = price * qty

        # ----------------------------- #
        # 1) 현금 잔고 업데이트
        # ----------------------------- #
        if side == "BUY":
            balance -= trade_value
        else:  # SELL
            balance += trade_value

        self.acc_repo.update_balance(account_id, balance)

        # ----------------------------- #
        # 2) 포지션 업데이트
        # ----------------------------- #
        pos = self.acc_repo.get_position(account_id, symbol)

        if side == "BUY":
            if not pos:
                # 신규 포지션
                self.acc_repo.insert_position(
                    account_id, symbol, qty, price
                )
            else:
                old_qty = pos["qty"]
                old_avg = pos["avg_price"]
                new_qty = old_qty + qty
                new_avg = (old_qty * old_avg + qty * price) / new_qty

                self.acc_repo.update_position(account_id, symbol, new_qty, new_avg)

        else:  # SELL
            if not pos:
                return

            old_qty = pos["qty"]
            new_qty = old_qty - qty

            if new_qty <= 0:
                self.acc_repo.delete_position(account_id, symbol)
            else:
                self.acc_repo.update_position(
                    account_id, symbol, new_qty, pos["avg_price"]
                )
