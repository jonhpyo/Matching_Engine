# api/services/db_login.py
import os
import random
import hashlib
from decimal import Decimal

import psycopg2
import psycopg2.extras


class LoginDB:
    """
    - 회원가입 / 로그인 / 계좌개설 전용 DB 헬퍼
    - HTS 쪽 DBService에서 쓰던 로직을 API 서버용으로 옮긴 버전
    """

    def __init__(
        self,
        host: str = "postgres",     # 도커 내에서는 서비스 이름
        dbname: str = "myhts",
        user: str = "myhts",
        password: str = "myhts_pw",
        port: int = 5432,
    ):
        self.conn = psycopg2.connect(
            host=host,
            dbname=dbname,
            user=user,
            password=password,
            port=port,
        )
        self.conn.autocommit = True

    # -----------------------------
    # 회원 관련
    # -----------------------------
    def insert_user(self, email: str, password: str) -> bool:
        """
        새 유저 생성 (회원가입)
        """
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO users (email, pw_hash, created_at)
                    VALUES (%s, %s, now());
                    """,
                    (email, pw_hash),
                )
                return True
            except psycopg2.Error as e:
                print("insert_user error:", e)
                return False

    def get_user_id_by_email(self, email: str) -> int | None:
        """
        이메일로 user_id 조회
        """
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            row = cur.fetchone()
            return row[0] if row else None

    def verify_user(self, email: str, password: str) -> int | None:
        """
        로그인용: 이메일 + 비밀번호 검증 후 user_id 반환 (실패 시 None)
        """
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, pw_hash FROM users WHERE email=%s",
                (email,),
            )
            row = cur.fetchone()

        if not row:
            return None

        user_id, stored_hash = row
        if stored_hash == pw_hash:
            return user_id
        return None

    # -----------------------------
    # 계좌 관련
    # -----------------------------
    def _account_no_exists(self, account_no: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM accounts WHERE account_no=%s",
                (account_no,),
            )
            return cur.fetchone() is not None

    def _generate_account_no(self) -> str:
        """
        계좌번호 생성: 예) 100-1234-5678
        """
        while True:
            body = "".join(str(random.randint(0, 9)) for _ in range(8))
            acc = f"100-{body[:4]}-{body[4:]}"
            if not self._account_no_exists(acc):
                print("[LoginDB] generate_account_no:", acc)
                return acc

    def create_account(self, user_id: int, name: str = "") -> str | None:
        """
        계좌 개설 (기본잔액: 환경변수 INITIAL_CASH, 없으면 10,000,000)
        """
        default_balance = Decimal(os.getenv("INITIAL_CASH", "10000000"))
        account_no = self._generate_account_no()

        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO accounts
                        (user_id, account_no, name, balance, created_at)
                    VALUES
                        (%s, %s, %s, %s, now());
                    """,
                    (user_id, account_no, name, default_balance),
                )
                return account_no
            except psycopg2.Error as e:
                print("create_account error:", e)
                return None

    def get_primary_account_id(self, user_id: int) -> int | None:
        """
        해당 유저의 첫 번째 계좌 id
        """
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM accounts WHERE user_id=%s ORDER BY id LIMIT 1;",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def close(self):
        self.conn.close()
