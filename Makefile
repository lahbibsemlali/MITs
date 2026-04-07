.PHONY: install run launch clean reset report dev build publish demo-gifs

VENV = .venv
PY   = $(VENV)/bin/python
PIP  = $(VENV)/bin/pip

install:
	python -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

run: launch

launch:
	$(PY) mits.py

dev:
	$(VENV)/bin/textual run --dev mits.py

report:
	$(PY) mits.py --report

demo-gifs:
	$(PIP) install -q pillow cairosvg
	$(PY) scripts/generate_demo_gifs.py

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
	rm -f ~/.local/share/mits/data.json ~/.config/mits/config.json ~/.local/share/mit/data.json ~/.config/mit/config.json ~/.forge/data.json

clean:
	rm -rf __pycache__ $(VENV) widgets/__pycache__ dist build *.egg-info
