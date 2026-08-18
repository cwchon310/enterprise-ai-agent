.PHONY: install run test lint docker-up clean

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	.venv/bin/uvicorn app.main:app --reload --port 8000

test:
	.venv/bin/pytest -v

lint:
	.venv/bin/python -m compileall app tests

docker-up:
	docker compose up --build -d

clean:
	rm -rf .venv __pycache__ .pytest_cache *.pyc agent.db*