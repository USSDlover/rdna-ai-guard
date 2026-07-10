# =============================================================================
# RDNA AI Guard — Single-container production image (Option B)
# Stage 1: Angular static build | Stage 2: FastAPI serves API + SPA
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — Build Frontend (Angular 19+/22)
# -----------------------------------------------------------------------------
FROM node:24-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/angular.json frontend/tsconfig.json frontend/tsconfig.app.json ./
COPY frontend/tsconfig.spec.json frontend/.postcssrc.json ./
COPY frontend/public ./public
COPY frontend/src ./src

RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2 — Final image: FastAPI + static Angular assets
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# Angular application builder emits browser assets under dist/<project>/browser
COPY --from=frontend-build /frontend/dist/frontend/browser ./static

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
