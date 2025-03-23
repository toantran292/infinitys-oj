.PHONY: up down web worker

up:
	docker-compose up --build

down:
	docker-compose down

web:
	docker-compose run --rm web

worker:
	docker-compose run --rm worker

shell:
	docker-compose run --rm web python manage.py shell
