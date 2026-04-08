FROM python:3.12-slim AS backend
WORKDIR /app
COPY pyproject.toml setup.cfg* ./
COPY src/ src/
COPY backend/ backend/
RUN pip install --no-cache-dir -r backend/requirements.txt && pip install --no-cache-dir -e .

FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY --from=backend /app /app
COPY --from=backend /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin
COPY --from=frontend /app/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend /app/frontend/public /app/frontend/public
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
