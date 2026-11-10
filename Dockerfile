# syntax=docker/dockerfile:1
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROOFLOOP_ENV=production \
    PROOFLOOP_DB=/app/backend/data/proofloop.db
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/dist /app/frontend/dist
RUN useradd --create-home --uid 10001 proofloop \
    && mkdir -p /app/backend/data \
    && chown -R proofloop /app
USER proofloop
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
