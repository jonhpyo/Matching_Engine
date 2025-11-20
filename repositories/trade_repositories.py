# repositories/trade_repositories.py

from psycopg2.extras import DictCursor

class TradeRepository:
    """
    체결(trades) 테이블 Repository
    - DB 접근 ONLY
    - 매칭 로직 없음
    """

    def __init__(self, conn):
        self.conn = conn

    # ---------------------------
    # INSERT
    # ---------------------------
    def insert_trade(self, user_id, account_id, symbol, side, price, qty,
                     buy_order_id=None, sell_order_id=None, remark=None):

        sql = """
            INSERT INTO trades (
                user_id, account_id, symbol, side,
                price, quantity, trade_time,
                buy_order_id, sell_order_id, remark
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s)
            RETURNING id;
        """

        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (
                    user_id, account_id, symbol, side,
                    price, qty,
                    buy_order_id, sell_order_id, remark
                ))
                trade_id = cur.fetchone()[0]
                self.conn.commit()
                return trade_id

        except Exception as e:
            print("[TradeRepository] insert_trade error:", e)
            self.conn.rollback()
            return None

    # ---------------------------
    # SELECT - 내 체결 목록
    # ---------------------------
    def get_trades_by_user(self, user_id, limit=100):
        sql = """
            SELECT 
                    a.account_no AS account_no,
                    t.symbol      AS symbol,
                    CASE
                        WHEN ob.user_id = %(user_id)s THEN 'BUY'
                        WHEN os.user_id = %(user_id)s THEN 'SELL'
                        ELSE 'N/A'
                    END AS side,
                    t.price       AS price,
                    t.quantity    AS quantity,
                    t.trade_time  AS trade_time,
                    ''::text      AS remark
                FROM trades t
                JOIN orders ob ON t.buy_order_id  = ob.id
                JOIN orders os ON t.sell_order_id = os.id
                JOIN accounts a ON (
                    (ob.user_id = %(user_id)s AND ob.account_id = a.id)
                    OR (os.user_id = %(user_id)s AND os.account_id = a.id)
                )
                WHERE ob.user_id = %(user_id)s OR os.user_id = %(user_id)s
                ORDER BY t.trade_time DESC
                LIMIT %(limit)s
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, {"user_id": user_id, "limit": limit})
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print("[TradeRepository] get_trades_by_user error:", e)
            # return []

