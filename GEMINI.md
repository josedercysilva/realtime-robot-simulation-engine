# GEMINI.md — Contexto do Projeto e Diretrizes do Agente

> **Projeto:** Simulação em Tempo Real de Robô Móvel Diferencial (Laboratório 2)  
> **Padrão de Linguagem:** C99 (`-std=c99 -pedantic`)  
> **Plataforma de Execução:** Linux / POSIX Threads (`pthread`, `rt`)

---

## 1. Visão Geral do Sistema

O projeto consiste na simulação concorrente em tempo real de um robô móvel com tração diferencial. O sistema opera em esquema **assíncrono e multi-taxa (multi-rate)** utilizando duas threads POSIX dedicadas:

| Thread | Período ($T$) | Frequência | Responsabilidade Principal |
| :--- | :---: | :---: | :--- |
| **Thread 1 (Piloto / Telemetria)** | `30 ms` | ~33,3 Hz | Gera entrada de controle $u(t)$, lê a postura $y_f(t)$ e grava os logs em arquivo. |
| **Thread 2 (Motor de Física)** | `50 ms` | 20,0 Hz | Integra a cinemática discreta do robô e atualiza a postura $y_f(t)$. |

### Comunicação Inter-threads (IPC)
- **Mecanismo:** Memória compartilhada protegida exclusivamente por mutex POSIX (`pthread_mutex_t`).
- **Protocolo de Prioridade:** Configurado obrigatoriamente com Herança de Prioridade (`PTHREAD_PRIO_INHERIT`) para prevenção de inversão de prioridade.
- **Isolamento de Estado:** Todo acesso aos dados compartilhados deve ser mediado pelas funções de acesso do módulo `shared_mem`.

---

## 2. Estrutura do Repositório

```text
lab2_robot_simulation/
├── .agents/
│   └── skills/
│       └── c-standards/
│           └── SKILL.md         # Diretivas estritas de C (BARR-C:2018, MISRA, JPL)
├── .docs/                       # Documentação de apoio e roteiro do laboratório
├── include/                     # Cabeçalhos públicos (.h)
│   ├── kinematics.h
│   ├── shared_mem.h
│   └── rt_timer.h
├── src/                         # Código-fonte executável (.c)
│   ├── main.c
│   ├── kinematics.c
│   ├── shared_mem.c
│   └── rt_timer.c
├── build/                       # Objetos compilados (.o) e binário final
├── scripts/                     # Scripts de apoio e plotagem
│   └── plot_results.py
├── data/                        # Logs ASCII de saída (simulation_log.txt)
├── GEMINI.md                    # Documento de contexto e diretrizes do agente
└── Makefile                     # Script de compilação unificado
```

---

## 3. Diretrizes de Compilação e Execução

### 3.1. Compilação
O projeto deve compilar sem nenhum aviso (*zero warnings*):
```bash
make
```

*Flags obrigatórias do compilador:*
```text
-Wall -Wextra -Werror -pedantic -std=c99 -pthread
```

### 3.2. Execução
```bash
./build/robot_sim
```

### 3.3. Pós-Processamento e Validação Gráfica
```bash
python3 scripts/plot_results.py
```
*Gera os gráficos de validação a partir dos dados gravados em `data/simulation_log.txt`.*

### 3.4. Limpeza
```bash
make clean
```
*Remove binários e objetos em `build/`, além dos arquivos de dados gerados em `data/`.*

---

## 4. Padrões de Código Obrigatórios

> [!IMPORTANT]
> O código deve seguir estritamente as diretrizes para software de missão crítica descritas em `.agents/skills/c-standards/SKILL.md` (BARR-C:2018, NASA JPL Power of Ten, MISRA C:2023).

1. **Alocação de Memória:**
   - Proibida alocação dinâmica (`malloc`, `calloc`, `realloc`, `free`) após o ciclo de inicialização. Uso mandatório de estruturas e buffers estáticos.
2. **Tipos Primitivos:**
   - Uso obrigatório de inteiros de largura fixa de `<stdint.h>` (`uint8_t`, `int32_t`, etc.) e tipos booleanos de `<stdbool.h>`.
3. **Validação Defensiva de Parâmetros:**
   - Toda função pública de interface (`API`) deve validar a nulidade de ponteiros e a consistência de valores de entrada antes de qualquer processamento.
4. **Temporização em Tempo Real:**
   - Temporizações periódicas de laço devem utilizar `clock_nanosleep` com `CLOCK_MONOTONIC` e a flag `TIMER_ABSTIME`, prevenindo acúmulo de *drift*.

---

## 5. Diretrizes para o Agente Antigravity

Ao inspecionar, criar ou refatorar componentes do projeto:
- **Desacoplamento de Módulos:** Manter separação estrita entre contratos públicos em `include/` e implementações privadas em `src/`.
- **Concorrência Segura:** Proibido o uso de variáveis globais desprotegidas; todo estado global ou compartilhado deve residir no módulo `shared_mem`.
- **Garantia de Integridade:** Assegurar que o código compile sob as flags estritas sem alertas (`-Werror`).
