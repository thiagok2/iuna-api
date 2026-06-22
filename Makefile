.PHONY: start dev test install clean

# Inicia a API (com hot-reload)
start:
	source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Alias
dev: start

# Roda os testes
test:
	source .venv/bin/activate && pytest

# Instala dependências
install:
	source .venv/bin/activate && pip install -r requirements.txt

# Limpa caches
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
