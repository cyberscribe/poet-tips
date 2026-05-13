.PHONY: all bootstrap phase0 phase1 phase2 phase3 phase4 phase5 lint

PYTHON := .venv/bin/python
GRAPHML := data/raw/poet_tips-20191025.graphml
GRAPHML_URL := https://archive.org/download/poet_tips-20191025/poet_tips-20191025.graphml
GRAPHML_SHA256 := 4aa9bafca51cbbbc04ced9bd4d71f5ce15276bd65af6b7d68ff2dd09f981bd7c

bootstrap: $(GRAPHML)

$(GRAPHML):
	mkdir -p data/raw
	curl -L --fail -o $@ $(GRAPHML_URL)
	echo "$(GRAPHML_SHA256)  $@" | shasum -a 256 -c -

all: phase1 phase2 phase3 phase4 phase5

phase0:
	$(PYTHON) src/phase0.py

phase1:
	$(PYTHON) src/phase1.py

phase2:
	$(PYTHON) src/phase2.py

phase3:
	$(PYTHON) src/phase3.py

phase4:
	$(PYTHON) src/phase4.py

phase5:
	$(PYTHON) src/phase5.py

lint:
	.venv/bin/ruff check src/
