FROM python:3.11-slim

WORKDIR /app

# requirements 먼저 복사
#COPY engine/requirements.txt ./requirements.txt
# 엔진 코드
COPY engine/ .
COPY services/ ./services

# 필요 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 실행 (엔진은 9000 포트)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
