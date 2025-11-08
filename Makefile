.PHONY: install format lint test run

install:
	pip install -r requirements.txt

format:
	@echo "No formatters configured yet"

lint:
	@echo "No linting configured yet"

test:
	pytest -q

run:
	streamlit run app/main.py
