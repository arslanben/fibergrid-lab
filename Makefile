.PHONY: up down reset logs ps test solve debug

up: ## Build and start the lab
	docker compose up -d --build

down: ## Stop the lab (keeps data)
	docker compose down

reset: ## Stop the lab and wipe the database volume
	docker compose down -v

logs: ## Follow container logs
	docker compose logs -f --tail=200

ps: ## Show container status
	docker compose ps

test: ## Run smoke tests against the running lab
	bash tests/smoke.sh

solve: ## Run the automated solver (SPOILER)
	python3 solve/solve.py

debug: ## Start with debug ports exposed (app:8000, db:5432)
	docker compose -f docker-compose.yml -f docker-compose.debug.yml up -d
