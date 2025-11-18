FROM python:3.11

# 1) 공통 작업 디렉토리
WORKDIR /app

# 2) 코드 복사 (폴더 구조 유지)
COPY api/ ./api
COPY services/ ./services

# 3) requirements 설치 (api 기준)
COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4) uvicorn 실행
#   - 작업 디렉토리: /app
#   - 모듈 경로   : api.main:app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
