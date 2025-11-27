FROM python:3.11-slim

WORKDIR /app

# system deps for WeasyPrint (minimal)
RUN apt-get update && apt-get install -y build-essential libpango-1.0-0 libpangocairo-1.0-0 libffi-dev shared-mime-info && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* /app/
RUN pip install poetry==1.8.1
RUN poetry config virtualenvs.create false && poetry install --no-root --only main

COPY . /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
