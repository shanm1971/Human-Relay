FROM python:3.14-slim
WORKDIR /app
COPY requirements.lock .
RUN grep -v '^pywin32==' requirements.lock > requirements-linux.txt && pip install --no-cache-dir -r requirements-linux.txt
COPY apps ./apps
COPY database ./database
RUN useradd --create-home relay
USER relay
CMD ["uvicorn", "apps.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
