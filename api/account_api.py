# api/account_api.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth_api import get_current_user
from repositories.account_repository import AccountRepository
from services.account_service import AccountService


# -----------------------------
# Pydantic Models
# -----------------------------
class OpenAccountIn(BaseModel):
    user_id: int
    account_no: str


# -----------------------------
# 라우터 팩토리
# -----------------------------
def create_account_router(account_repo: AccountRepository, account_service: AccountService):
    router = APIRouter()

    # -------------------------------------------------------
    # 1) 계좌 개설
    # -------------------------------------------------------
    @router.post("/account/open")
    def open_account(body: OpenAccountIn, user=Depends(get_current_user)):

        if user.user_id != body.user_id:
            raise HTTPException(status_code=403, detail="User ID mismatch")

        new_id = account_repo.create_account(
            user_id=body.user_id,
            account_no=body.account_no
        )

        return {"account_id": new_id}

    # -------------------------------------------------------
    # 2) 기본 계좌 조회
    # -------------------------------------------------------
    @router.get("/account/primary")
    def primary_account(user=Depends(get_current_user)):
        user_id = user.user_id
        acc_id = account_service.get_primary_account(user_id)
        return {"account_id": acc_id}

    # -------------------------------------------------------
    # 3) 계좌 요약 조회
    # -------------------------------------------------------
    @router.get("/account/summary")
    def summary(account_id: int, user=Depends(get_current_user)):

        # 계좌 소유자 확인
        owner = account_repo.get_user_id_by_account(account_id)
        if owner != user.user_id:
            raise HTTPException(403, "Forbidden")

        summary = account_repo.get_account_summary(account_id)
        return summary

    # -------------------------------------------------------
    # 4) 유저 전체 계좌 목록
    # -------------------------------------------------------
    @router.get("/account/list")
    def account_list(user=Depends(get_current_user)):
        rows = account_repo.get_accounts_by_user(user.user_id)
        return rows

    return router
