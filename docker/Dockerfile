FROM python:3.11-slim

WORKDIR /app

# Copy everything needed for install
COPY pyproject.toml .
COPY src/ src/

# Install (non-editable for Docker)
RUN pip install --no-cache-dir ".[lab-ml,dev]"

# Copy configs and scripts
COPY configs/ configs/
COPY scripts/ scripts/

# Non-root user for security
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

CMD ["uvicorn", "polytwin.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
