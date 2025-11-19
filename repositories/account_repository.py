# repositories/account_repository.py
import psycopg2
from psycopg2.extras import DictCursor


class AccountRepository:
    def __init__(self, conn):
        self.conn = conn

    # -----------------------------------------
    # 계좌 개설
    # -----------------------------------------
    def create_account(self, user_id: int, account_no: str):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (user_id, account_no, balance)
                VALUES (%s, %s, 0)
                RETURNING id;
                """,
                (user_id, account_no),
            )
            new_id = cur.fetchone()[0]
        self.conn.commit()
        return new_id

    # -----------------------------------------
    # 기본 계좌 조회 (가장 먼저 생성된 계좌)
    # -----------------------------------------
    def get_primary_account_id(self, user_id: int):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id 
                FROM accounts
                WHERE user_id=%s
                ORDER BY id
                LIMIT 1;
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    # -----------------------------------------
    # 계좌 ID로 해당 계좌의 user_id 조회
    # -----------------------------------------
    def get_user_id_by_account(self, account_id: int):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT user_id FROM accounts WHERE id=%s;",
                (account_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    # -----------------------------------------
    # 계좌 요약 (잔고 + 포지션)
    # -----------------------------------------
    def get_account_summary(self, account_id: int):
        summary = {"balance": 0.0, "positions": []}

        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            # 잔고
            cur.execute("SELECT balance FROM accounts WHERE id=%s;", (account_id,))
            row = cur.fetchone()
            summary["balance"] = float(row["balance"]) if row else 0.0

            # 포지션
            cur.execute(
                """
                SELECT symbol, qty, avg_price, updated_at
                FROM positions
                WHERE account_id=%s
                ORDER BY symbol;
                """,
                (account_id,)
            )
            rows = cur.fetchall()

            summary["positions"] = [
                {
                    "symbol": r["symbol"],
                    "qty": float(r["qty"]),
                    "avg_price": float(r["avg_price"]),
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

        return summary

    # -----------------------------------------
    # 유저 전체 계좌 목록
    # -----------------------------------------
    def get_accounts_by_user(self, user_id: int):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, account_no, name, balance
                FROM accounts
                WHERE user_id=%s
                ORDER BY id;
                """,
                (user_id,),
            )
            return cur.fetchall()

    # -----------------------------------------
    # 잔고 업데이트
    # -----------------------------------------
    def update_balance(self, account_id: int, new_balance: float):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE accounts SET balance=%s WHERE id=%s;",
                (new_balance, account_id)
            )
        self.conn.commit()

    # -----------------------------------------
    # 포지션 조회
    # -----------------------------------------
    def get_position(self, account_id: int, symbol: str):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT account_id, symbol, qty, avg_price
                FROM positions
                WHERE account_id=%s AND symbol=%s;
                """,
                (account_id, symbol),
            )
            return cur.fetchone()

    # -----------------------------------------
    # 포지션 신규 생성
    # -----------------------------------------
    def insert_position(self, account_id: int, symbol: str, qty: float, avg_price: float):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO positions (account_id, symbol, qty, avg_price)
                VALUES (%s, %s, %s, %s);
                """,
                (account_id, symbol, qty, avg_price),
            )
        self.conn.commit()

    # -----------------------------------------
    # 포지션 업데이트
    # -----------------------------------------
    def update_position(self, account_id: int, symbol: str, qty: float, avg_price: float):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE positions
                SET qty=%s, avg_price=%s
                WHERE account_id=%s AND symbol=%s;
                """,
                (qty, avg_price, account_id, symbol),
            )
        self.conn.commit()

    # -----------------------------------------
    # 포지션 삭제
    # -----------------------------------------
    def delete_position(self, account_id: int, symbol: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM positions WHERE account_id=%s AND symbol=%s;",
                (account_id, symbol),
            )
        self.conn.commit()
