up: 
	sudo docker-compose up --build -d

web-build:
	sudo docker-compose up --build -d web

web-logs:
	sudo docker-compose logs -f web

stop: 
	sudo docker-compose stop

logs: 
	sudo docker-compose logs -f main

logs-db: 
	sudo docker-compose logs -f db

shell: 
	sudo docker-compose exec main tortoise-cli shell
