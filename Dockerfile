FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QUOTA_DB_PATH=/app/data/quota.sqlite3

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser . ./
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

EXPOSE 8504
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8504", "--server.headless=true", "--browser.gatherUsageStats=false"]
