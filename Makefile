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

test: up wait_for_rabbitmq
	docker-compose exec $(SERVICE_NAME) pytest -vv

wait_for_rabbitmq:
	@echo "Waiting for RabbitMQ to be ready..."
	@sleep 5
	@until docker-compose exec rabbitmq bash -c 'rabbitmqctl ping' > /dev/null 2>&1; do \
		echo "RabbitMQ is not ready yet. Waiting..."; \
		sleep 1; \
	done
	@echo "RabbitMQ is ready!"
