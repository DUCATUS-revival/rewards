run: 
	sudo docker-compose up --build -d

shell: 
	sudo docker-compose exec rewards tortoise-cli shell