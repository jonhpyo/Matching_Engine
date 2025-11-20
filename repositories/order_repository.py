# repositories/order_repository.py
import psycopg2
from psycopg2.extras import DictCursor


class OrderRepository:
    def __init__(self, conn):
        self.conn = conn

    def bucket_by_price(self, symbol: str):
        sql = """
            SELECT price, side, SUM(remaining_qty) AS qty, COUNT(*) AS cnt
            FROM orders
            WHERE symbol = %s
              AND remaining_qty > 0
            GROUP BY price, side
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, (symbol,))
            return cur.fetchall()

    # repositories/order_repository.py

    def get_price_stats(self, symbol):
        sql = """
            SELECT price,
                   SUM(remaining_qty) AS qty,
                   COUNT(*) AS cnt
            FROM orders
            WHERE symbol = %s
              AND status IN ('WORKING', 'PARTIAL')
            GROUP BY price
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, (symbol,))
                rows = cur.fetchall()

            result = {}
            for price, qty, cnt in rows:
                result[str(price)] = {
                    "qty": float(qty),
                    "cnt": int(cnt)
                }

            return result

        except Exception as e:
            print("[OrderRepository] get_price_stats error:", e)
            return {}

    # repositories/order_repository.py (추가)

    def get_grouped_orderbook(self, symbol: str):
        sql = """
            SELECT side,
                   price,
                   SUM(remaining_qty) AS qty,
                   COUNT(*) AS cnt
            FROM orders
            WHERE symbol = %s
              AND status IN ('WORKING','PARTIAL')
              AND remaining_qty > 0
            GROUP BY side, price
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(sql, (symbol,))
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print("[OrderRepository] get_grouped_orderbook error:", e)
            return []


    # -------------------------------------------
    # 신규 주문 삽입
    # -------------------------------------------
    def insert_order(self, **kwargs):
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    INSERT INTO orders (user_id, account_id, symbol, side, price, quantity, remaining_qty, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, (
                    kwargs["user_id"], kwargs["account_id"], kwargs["symbol"],
                    kwargs["side"], kwargs["price"], kwargs["quantity"],
                    kwargs["remaining_qty"], kwargs["status"],
                ))
                order_id = cur.fetchone()["id"]
            self.conn.commit()
            return order_id

        except Exception as e:
            self.conn.rollback()
            print("🔥 [insert_order SQL ERROR]", e)
            print("🔥 SQL DATA:", kwargs)
            raise

    # -------------------------------------------
    # 주문 조회 (MatchingEngine 용)
    # -------------------------------------------
    def get_order(self, order_id):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT id, user_id, account_id, symbol, side, price,
                       quantity, remaining_qty, status, created_at
                FROM orders
                WHERE id = %s
            """, (order_id,))
            r = cur.fetchone()
            if not r:
                return None

            # 매칭엔진이 요구하는 dict 형태로 표준화
            return {
                "id": r["id"],
                "user_id": r["user_id"],
                "account_id": r["account_id"],
                "symbol": r["symbol"].upper(),
                "side": r["side"].upper(),
                "price": float(r["price"]),
                "remaining_qty": float(r["remaining_qty"]),
                "qty": float(r["quantity"]),  # optional
            }

    # -------------------------------------------
    # 잔량 / 상태 업데이트
    # -------------------------------------------
    def update_order_remaining(self, order_id, remaining_qty, status=None):
        with self.conn.cursor() as cur:
            if status:
                cur.execute(
                    """
                    UPDATE orders
                    SET remaining_qty=%s, status=%s, updated_at=NOW()
                    WHERE id=%s;
                    """,
                    (remaining_qty, status, order_id)
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET remaining_qty=%s, updated_at=NOW()
                    WHERE id=%s;
                    """,
                    (remaining_qty, order_id)
                )
            self.conn.commit()

    # -------------------------------------------
    # 미체결 주문 조회
    # -------------------------------------------
    def get_working_orders_by_user(self, user_id, limit=100):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, symbol, side, price,
                       quantity, remaining_qty, created_at
                FROM orders
                WHERE user_id=%s
                  AND status IN ('WORKING','PARTIAL')
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (user_id, limit)
            )
            return [dict(r) for r in cur.fetchall()]

    # -------------------------------------------
    # 주문 취소
    # -------------------------------------------
    def cancel_orders(self, order_ids):
        if not order_ids:
            return 0

        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE orders
                SET status='CANCELLED', remaining_qty=0, updated_at=NOW()
                WHERE id = ANY(%s)
                  AND status IN ('WORKING','PARTIAL');
                """,
                (order_ids,)
            )
            affected = cur.rowcount
            self.conn.commit()
            return affected
