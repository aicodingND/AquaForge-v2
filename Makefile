# SwimAI Docker Quick Commands
# Windows: Use with WSL or install make for Windows

.PHONY: help dev prod stop clean logs build rebuild test

help: ## Show this help
	@echo "SwimAI Docker Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev: ## Start in development mode (hot reload)
	docker-compose --profile dev up

prod: ## Start in production mode
	docker-compose --profile prod up -d

stop: ## Stop all containers
	docker-compose down

clean: ## Stop and remove volumes (fresh start)
	docker-compose down -v

logs: ## View logs
	docker-compose logs -f

build: ## Build images
	docker-compose build

rebuild: ## Rebuild and start (dev)
	docker-compose --profile dev up --build

test: ## Run tests in container
	docker-compose --profile dev run --rm swimai-dev pytest

shell: ## Open shell in dev container
	docker-compose --profile dev run --rm swimai-dev /bin/bash

db: ## Start with database
	docker-compose --profile dev --profile db up
