FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y netcat-openbsd
    
RUN pip install --upgrade pip wheel "poetry==2.1.4" && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock alembic.ini start.sh ./

RUN chmod +x start.sh

RUN poetry install --no-interaction --no-ansi --no-root

COPY src ./src

ENV PYTHONPATH="/app/src"

ENTRYPOINT ["./start.sh", "python", "src/app/service.py", "--config", "config.yaml"]

EXPOSE 8002