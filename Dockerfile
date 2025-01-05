FROM python:3.11-slim


RUN pip install poetry==1.8.5

ENV POETRY_CACHE_DIR=/tmp/poetry_cache
ENV POETRY_VIRTUALENVS_PATH=/opt/venv

WORKDIR /app

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

COPY . /app

EXPOSE 8080

ENTRYPOINT ["poetry", "run", "python", "-m", "niimprint", "server"]
