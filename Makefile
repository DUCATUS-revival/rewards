compose := docker-compose
lines := 1000

pre-commit:
	pip install pre-commit --upgrade
	pre-commit install

build:
	sudo  $(compose) up --build -d

main-build: 
	sudo  $(compose) up --build -d main

main-logs:
	sudo  $(compose) logs -f --tail $(lines) main

web-build:
	sudo  $(compose) up --build -d web

web-logs:
	sudo  $(compose) logs -f --tail $(lines) web

logs: 
	sudo  $(compose) logs -f --tail $(lines)

db-logs:
	sudo  $(compose) logs -f --tail $(lines) db

shell: 
	sudo  $(compose) exec web tortoise-cli shell

down: 
	sudo  $(compose) down

init-aerich:
	sudo $(compose) exec web aerich init -t src.settings.TORTOISE_ORM

init-db:
	sudo $(compose) exec web aerich init-db

migrate-db:
	sudo $(compose) exec web aerich migrate

upgrade-db:
	sudo $(compose) exec web aerich upgrade

downgrade-db:
	sudo $(compose) exec web aerich downgrade

full-migrate: migrate-db upgrade-db
