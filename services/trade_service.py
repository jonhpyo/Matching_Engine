class TradeService:
    def __init__(self, repo):
        self.repo = repo

    def insert_trade(self, **kwargs):
        return self.repo.insert_trade(**kwargs)

    def get_trades_by_user(self, user_id: int, limit: int = 100):
        return self.repo.get_trades_by_user(user_id, limit)
