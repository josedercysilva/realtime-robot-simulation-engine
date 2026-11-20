PRJ := ./build/robot_sim

SRCDIR := ./src
INCDIR := ./include
OBJDIR := ./build
VENV := ./.venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

CC := gcc
CFLAGS := -std=c99 -pedantic -I $(INCDIR) -I $(SRCDIR) -Wall -Wextra -Werror -g -O0 -DDEBUG -MMD -MP -pthread
LDLIBS := -pthread -lrt -lm
LDFLAGS :=

sources := $(wildcard $(SRCDIR)/*.c)
objects := $(patsubst %.c, $(OBJDIR)/%.o, $(notdir $(sources)))

vpath %.c $(SRCDIR)

all: $(PRJ)

$(OBJDIR):
	mkdir -p $(OBJDIR) data

$(OBJDIR)/%.o: %.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(PRJ): $(objects)
	$(CC) $(LDFLAGS) $(objects) $(LDLIBS) -o $(PRJ)

run: $(PRJ)
	$(PRJ)

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install numpy matplotlib

plot: $(VENV)/bin/activate
	$(PYTHON) -B scripts/plot_results.py

sim: run plot

benchmark: $(PRJ) $(VENV)/bin/activate
	$(PYTHON) -B scripts/run_stress_and_plot.py

help:
	@echo "============================================================="
	@echo " Lab 2: Simulação de Robô Móvel em Tempo Real (UFAM / FTL066)"
	@echo "============================================================="
	@echo " Alvos disponíveis:"
	@echo "   make            - Compila o binário da simulação ($(PRJ))"
	@echo "   make run        - Executa apenas a simulação nominal em C (sem carga)"
	@echo "   make plot       - Cria .venv e gera os gráficos da simulação nominal"
	@echo "   make sim        - Simulação nominal: 'run' seguido de 'plot' (sem carga)"
	@echo "   make benchmark  - Simulação completa e comparativa (Sem Carga vs. Com Carga + gráficos)"
	@echo "   make clean      - Remove artefatos de compilação (build/) e dados gerados (data/)"
	@echo "   make clean-venv - Remove o ambiente virtual Python ($(VENV))"
	@echo "   make help       - Exibe esta mensagem de ajuda"
	@echo "============================================================="

.PHONY: all clean clean-venv run plot sim benchmark help

clean:
	rm -rf $(OBJDIR) data/*.txt data/*.png scripts/__pycache__

clean-venv:
	rm -rf $(VENV) scripts/__pycache__

-include $(objects:.o=.d)
