# Python 3.10 슬림 이미지를 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    libpq-dev gcc postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
# 환경 변수 설정 (이 부분은 .env 파일을 사용하여 설정)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 포트 개방 (Django의 기본 포트 8000)
EXPOSE 8000

# 애플리케이션 실행 명령어
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
