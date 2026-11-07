VENV := ./.venv
PYTHON := $(VENV)/bin/python3
SCRIPT := sim_circuit.py

all: run

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

venv: $(VENV)/bin/activate

run: $(VENV)/bin/activate
	$(PYTHON) -B $(SCRIPT)

help:
	@echo "============================================================="
	@echo " Simulador Interativo 2D - Lab 2 (Robô Móvel Diferencial)"
	@echo "============================================================="
	@echo " Alvos disponíveis:"
	@echo "   make            - Cria o .venv (se necessário) e abre a simulação"
	@echo "   make run        - Executa o simulador interativo imediatamente"
	@echo "   make venv       - Cria e configura apenas o ambiente .venv"
	@echo "   make clean      - Remove arquivos de cache (__pycache__)"
	@echo "   make clean-venv - Remove o ambiente virtual (.venv)"
	@echo "   make help       - Exibe esta mensagem de ajuda"
	@echo "============================================================="

.PHONY: all venv run clean clean-venv help

clean:
	rm -rf __pycache__

clean-venv: clean
	rm -rf $(VENV)
