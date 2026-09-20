FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

RUN useradd --system --uid 1001 --home-dir /srv wafuser \
    && chown -R wafuser:wafuser /srv
USER wafuser

EXPOSE 8080
CMD ["gunicorn", "-c", "gunicorn.conf.py", "--bind", "0.0.0.0:8080", \
     "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", \
     "waf:app"]
