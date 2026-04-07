.PHONY: install run launch clean reset report dev build publish

VENV = .venv
PY   = $(VENV)/bin/python
PIP  = $(VENV)/bin/pip

install:
	python -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

run: launch

launch:
	$(PY) mit.py

dev:
	$(VENV)/bin/textual run --dev mit.py

report:
	$(PY) mit.py --report

build:
	$(PY) -m pip install -q build
	rm -rf dist
	$(PY) -m build

# Upload to PyPI (requires TWINE_USERNAME / TWINE_PASSWORD or API token)
publish: build
	$(PY) -m pip install -q twine
	$(PY) -m twine check dist/*
	@echo "Run: $(PY) -m twine upload dist/*"

reset:
	rm -f ~/.local/share/mit/data.json ~/.config/mit/config.json ~/.forge/data.json

clean:
	rm -rf __pycache__ $(VENV) widgets/__pycache__ dist build *.egg-info
