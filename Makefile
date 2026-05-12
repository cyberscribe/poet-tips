.PHONY: all phase0 phase1 phase2 phase3 phase4 phase5 lint

PYTHON := .venv/bin/python

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
