.PHONY: train serve build up down logs test lint

# ── Modelos ────────────────────────────────────────────────────────────────────
# Entrena + bendice los modelos en data/09_serving/
# (tarda: descarga datos de la CDC y entrena XGBoost)
train:
	kedro run --pipeline nhanes_2015
	kedro run --pipeline serving

# ── Desarrollo local (sin Docker) ─────────────────────────────────────────────
serve:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# ── Docker ────────────────────────────────────────────────────────────────────
# Build manual de la imagen de la API (desde raiz, como indica el Dockerfile)
build:
	docker build -f api/Dockerfile -t ev3-api .

# Levantar api + web en background
up:
	docker compose up --build -d

# Bajar contenedores
down:
	docker compose down

# Ver logs en tiempo real (Ctrl+C para salir)
logs:
	docker compose logs -f

# ── Calidad ───────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

lint:
	ruff check .
