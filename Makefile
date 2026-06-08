.PHONY: run test lint

run:
	streamlit run app/streamlit_app.py

test:
	pytest tests/ -v

lint:
	flake8 src/ app/ tests/
	black src/ app/ tests/
