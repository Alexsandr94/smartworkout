.PHONY: db-up db-up-ui db-down start start-ui

# Старт базы данных без ui
db-up:
	docker compose up -d

# Старт базы данных с ui интерфейсом
db-up-ui:
	docker compose --profile tools up -d

db-down:
	docker compose down

start: db-up
	python3 ./main.py

start-ui: db-up-ui
	python3 ./main.py

# Создание пользователя с ролью admin
create-admin:
	python3 -m scripts.create_admin