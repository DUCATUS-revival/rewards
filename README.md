# Rewards backend
Service for collecting statistics of nodes online and sending rewards for it

## Configuration
Create `config.yaml` according to `config.example.yaml`

## Run
```bash
sudo docker-compose up --build -d
```

## ORM

```bash
sudo docker-compose exec rewards tortoise-cli shell
```

