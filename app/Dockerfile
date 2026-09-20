FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .
RUN python tools/gen_export.py

RUN useradd --system --uid 1001 --home-dir /srv appuser \
    && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", \
     "--access-logfile", "-", "--error-logfile", "-", "main:app"]
