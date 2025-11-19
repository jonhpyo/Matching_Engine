FROM python:3.12

WORKDIR /app

# 전체 프로젝트를 복사한다
COPY . .

RUN pip install -r api/requirements.txt
RUN pip install -r services/requirements.txt

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "9000"]
