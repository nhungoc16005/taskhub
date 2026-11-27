FROM python:3.12-slim-bookworm AS build

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --gid 10001 taskhub \
    && useradd --uid 10001 --gid taskhub --create-home taskhub
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --chown=taskhub:taskhub app ./app
COPY --chown=taskhub:taskhub alembic ./alembic
COPY --chown=taskhub:taskhub alembic.ini .
COPY --chown=taskhub:taskhub --chmod=755 docker/entrypoint.sh /usr/local/bin/taskhub-entrypoint

USER taskhub
EXPOSE 8000
ENTRYPOINT ["taskhub-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
