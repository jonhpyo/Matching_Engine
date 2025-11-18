# services/db_matching.py
import os
import hashlib
import psycopg2
import psycopg2.extras


class MatchingDB:
    """
    매칭 서버 전용 DB 어댑터.
    - SimAccount, Qt, UI 등에 일절 의존하지 않고
    - orders / trades / accounts / positions 테이블만 다룸
    """

    def __init__(
        self,
        host: str | None = None,
        dbname: str | None = None,
        user: str | None = None,
        password: str | None = None,
        port: int | None = None,
    ):
        self.host = host or os.getenv("DB_HOST", "host.docker.internal")
        self.dbname = dbname or os.getenv("DB_NAME", "myhts")
        self.user = user or os.getenv("DB_USER", "myhts")
        self.password = password or os.getenv("DB_PASSWORD", "myhts_pw")
        self.port = port or int(os.getenv("DB_PORT", "5432"))

        self.conn = psycopg2.connect(
            host=self.host,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            port=self.port,
        )
        # 매칭은 트랜잭션 단위로 처리 → autocommit 끔
        self.conn.autocommit = False

        # ---------- 로그인용 유저 조회 ----------

    def verify_user(self, email: str, password: str):
        """
        users 테이블 기반 로그인 검증.
        - 패스워드는 sha256으로 해시해서 pw_hash와 비교
        - 성공 시 (user_id, primary_account_id) 반환
        - 실패 시 (None, None) 반환
        """
        pw_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        from psycopg2.extras import DictCursor
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id
                FROM users
                WHERE email = %s
                  AND pw_hash = %s;
                """,
                (email, pw_hash),
            )
            row = cur.fetchone()

        if not row:
            return None, None

        user_id = row["id"]

        # 해당 유저의 기본 계좌 (가장 먼저 만든 계좌 하나) 조회
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT id, account_no, balance
                FROM accounts
                WHERE user_id = %s
                ORDER BY id
                LIMIT 1;
                """,
                (user_id,),
            )
            acc = cur.fetchone()

        if not acc:
            return user_id, None

        primary_account_id = acc["id"]
        return user_id, primary_account_id

    # ---------- 공용 유틸 ----------

    def get_active_symbols(self) -> list[str]:
        """WORKING/PARTIAL 주문이 존재하는 심볼 목록"""
        from psycopg2.extras import DictCursor

        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT symbol
                FROM orders
                WHERE status IN ('WORKING','PARTIAL');
                """
            )
            return [row["symbol"] for row in cur.fetchall()]

    # ---------- 매칭에 필요한 쿼리들 ----------

    def fetch_working_orders(self, symbol: str):
        """
        해당 심볼의 WORKING/PARTIAL 주문을 가격/시간 순으로 가져온다.
        (BUY: 가격 내림차순, SELL: 가격 오름차순 정렬은
         MatchingEngine 쪽에서 side별로 나눠서 처리)
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM orders
                WHERE symbol = %s
                  AND status IN ('WORKING','PARTIAL')
                ORDER BY created_at ASC;
                """,
                (symbol,),
            )
            return cur.fetchall()

    def insert_trade_record(self, buy, sell, symbol: str, price: float, qty: float):
        """
        trades 테이블에 한 건의 체결 추가
        (현재 DB 스키마: buy_order_id, sell_order_id, symbol, price, quantity, trade_time)
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trades
                    (buy_order_id, sell_order_id, symbol, price, quantity, trade_time)
                VALUES
                    (%s, %s, %s, %s, %s, now());
                """,
                (buy["id"], sell["id"], symbol, price, qty),
            )

    def update_order(self, order_id: int, remaining_qty: float, status: str):
        """주문 잔량/상태 업데이트"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE orders
                SET remaining_qty = %s,
                    status        = %s,
                    updated_at    = now()
                WHERE id = %s;
                """,
                (remaining_qty, status, order_id),
            )

    def update_account_balance(self, account_id: int, delta: float):
        """accounts.balance += delta"""
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE accounts SET balance = balance + %s WHERE id = %s;",
                (delta, account_id),
            )

    def update_position_on_trade(
        self,
        account_id: int,
        user_id: int,
        symbol: str,
        side: str,
        price: float,
        qty: float,
    ):
        """
        DBService.update_position_on_trade 를 거의 그대로 가져온 버전.
        (SimAccount 없이 순수 DB만 갱신)
        """
        conn = self.conn
        side = side.upper()
        try:
            with conn.cursor() as cur:
                # 기존 포지션 조회
                cur.execute(
                    "SELECT qty, avg_price FROM positions WHERE account_id=%s AND symbol=%s;",
                    (account_id, symbol),
                )
                row = cur.fetchone()

                if row:
                    old_qty, old_avg = float(row[0]), float(row[1])
                else:
                    old_qty, old_avg = 0.0, 0.0

                new_qty = old_qty
                new_avg = old_avg

                if side == "BUY":
                    total_cost = old_qty * old_avg + qty * price
                    new_qty = old_qty + qty
                    new_avg = total_cost / new_qty if new_qty > 0 else 0.0
                elif side == "SELL":
                    new_qty = old_qty - qty
                    if new_qty < 0:
                        new_qty = 0.0  # 공매도 미지원 가정
                    # 평균단가는 매도 시 유지

                if row:
                    if new_qty > 0:
                        cur.execute(
                            """
                            UPDATE positions
                            SET qty=%s, avg_price=%s, updated_at=now()
                            WHERE account_id=%s AND symbol=%s;
                            """,
                            (new_qty, new_avg, account_id, symbol),
                        )
                    else:
                        cur.execute(
                            "DELETE FROM positions WHERE account_id=%s AND symbol=%s;",
                            (account_id, symbol),
                        )
                else:
                    cur.execute(
                        """
                        INSERT INTO positions (user_id, account_id, symbol, qty, avg_price, updated_at)
                        VALUES (%s, %s, %s, %s, %s, now());
                        """,
                        (user_id, account_id, symbol, qty, price),
                    )
        except Exception as e:
            print("[MatchingDB] update_position_on_trade error:", e)
            raise

    def get_trades_by_user(self, user_id: int, limit: int = 100):
        """
        trades 테이블 기준으로 특정 사용자의 체결내역 조회
        - BUY 또는 SELL 주문 중 어느 한쪽이라도 user_id가 일치하면 포함
        - UI용 컬럼: account_no, symbol, side, price, quantity, trade_time, remark
        """
        from psycopg2.extras import DictCursor

        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
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
                LIMIT %(limit)s;
                """,
                {"user_id": user_id, "limit": limit},
            )
            rows = cur.fetchall()
            print(f"[DBService] get_trades_by_user({user_id}) -> {len(rows)} rows")
            return rows

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
