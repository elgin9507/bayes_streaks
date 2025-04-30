SERVICE_NAME="app"

build:
	docker-compose build

up:
	docker-compose up -d

buildup: build up

down:
	docker-compose down

logs:
	docker-compose logs -f

shell: up
	docker-compose exec $(SERVICE_NAME) bash

run_scenario: up
	docker-compose exec $(SERVICE_NAME) python run_scenario.py

test: up
	docker-compose exec $(SERVICE_NAME) pytest -vv
