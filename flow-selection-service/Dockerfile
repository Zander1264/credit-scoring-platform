FROM python:3.12-slim

WORKDIR /app

RUN pip install --upgrade pip wheel "poetry==2.1.4" && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-interaction --no-ansi --no-root

COPY src ./src

ENV PYTHONPATH="/app/src"

ENTRYPOINT ["python", "src/app/service.py", "--config", "config.yaml"]

EXPOSE 8000