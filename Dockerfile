FROM python:3.14-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY apps ./apps
COPY database ./database
RUN useradd --create-home relay
USER relay
CMD ["uvicorn", "apps.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
