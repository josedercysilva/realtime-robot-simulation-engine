Aqui está a **especificação técnica detalhada de arquitetura e estrutura de diretórios** do projeto em C para o Laboratório 2, elaborada da perspectiva de um **Líder de Arquitetura de Software Embarcado / Tempo Real**:

# Especificação Técnica de Arquitetura de Projeto e Estrutura de Diretórios

## Projeto: Laboratório 2 – Simulação de Sistema de Tempo Real (Robô Diferencial) \| Autor: Líder de Arquitetura de Software Embarcado / Tempo Real

### 1\. Visão do Líder & Visão Geral da Arquitetura

Como líder do projeto, a nossa meta não é apenas entregar a simulação do robô móvel para o horizonte de \\\\(t \\in 2\\text{s}\\\\) 3, mas estabelecer uma **estrutura reutilizável e modular** que servirá de base para os laboratórios subsequentes (Lab 3 e Lab 4\) 4\.  
A arquitetura do sistema em C é baseada em **duas threads independentes** que operam em um esquema de **Duplo Produtor-Consumidor Cruzado (Assíncrono e Multi-taxa)** 5, 6:

* **Thread 1 (Piloto e Telemetria \- Período de 30 ms):** Define o vetor de controle \\\\(u(t) \= v, \\omega^T\\\\), lê a posição \\\\(y\_f(t)\\\\), exibe no console e persiste os logs em arquivo ASCII 4, 7\.  
* **Thread 2 (Motor de Simulação Física \- Período de 50 ms):** Lê o comando \\\\(u(t)\\\\), calcula a integração da equação de estados do robô diferencial e atualiza a postura da frente do robô \\\\(y\_f(t)\\\\) 1, 3, 7\.  
* **Mapeamento de Comunicação:** A troca de dados é realizada **exclusivamente** via módulo de **Memória Compartilhada Protegida** (\\\\(u\\\\) e \\\\(y\_f\\\\) sob pthread\_mutex) 4, 8\.

### 2\. Especificação Completa da Hierarquia de Diretórios

A estrutura do repositório deve ser rigorosamente organizada na seguinte árvore de arquivos:

```
lab2_rt_robot/
├── Makefile                 # Script de compilação principal unificado na raiz
├── README.md                # Guia rápido de compilação, requisitos e execução
│
├── include/                 # Interfaces públicas e definições de dados (.h)
│   ├── shared_mem.h         # Estrutura do buffer e protótipos de exclusão mútua (mutex)
│   ├── physics.h            # Protótipos das equações de estado e cinemática do robô
│   ├── telemetry.h          # Protótipos de geração de u(t), logging e métricas de tempo real
│   └── timer_rt.h           # Utilidades para temporização determinística (clock_nanosleep)
│
├── src/                     # Implementações do código-fonte (.c)
│   ├── main.c               # Ciclo de vida: criação das threads, inicialização e cleanup
│   ├── shared_mem.c         # Gerenciamento thread-safe dos dados compartilhados
│   ├── physics.c            # Integração numérica da cinemática do robô (50 ms)
│   ├── telemetry.c          # Geração de u(t), leitura de y_f(t) e arquivo .txt (30 ms)
│   └── timer_rt.c           # Medição de período real T(k) e cálculo de jitter J(k)
│
├── build/                   # Artefatos gerados na compilação (.o e executável)
│   └── robot_sim            # Executável do projeto
│
├── scripts/                 # Scripts de apoio e pós-processamento de dados
│   └── plot_results.py      # Script Python/Octave para plotagem do gráfico da trajetória
│
├── data/                    # Armazenamento de arquivos de dados gerados na execução
│   └── simulation_output.txt # Arquivo ASCII contendo t, u(t) e y_f(t)
│
└── doc/                     # Relatório e documentação do laboratório
    └── relatorio_lab2.pdf   # Relatório final
```

### 3\. Justificativa Arquitetural (Para Inclusão no Relatório)

Esta hierarquia atende diretamente aos requisitos do roteiro 4, 9 com os seguintes argumentos de engenharia de software:

* **Separação de Interface e Implementação (Desacoplamento):** Os arquivos em include/ expõem apenas a API pública de cada componente. A lógica interna está isolada em src/. Isso permite alterar a implementação de uma thread sem impactar o resto do sistema.  
* **Reutilização de Código para os Próximos Laboratórios (Item 1 do Roteiro):** Os módulos shared\_mem (comunicação thread-safe) e timer\_rt (relógio de tempo real de alta precisão) são genéricos. Eles poderão ser reusados sem modificações no Lab 3 e Lab 4\. O motor de simulação em physics.c poderá ser facilmente reaproveitado ao adicionar malhas fechadas de controle.  
* **Compilação Automatizada e Limpa (Makefile):** O professor pode descompactar o arquivo .zip, rodar make na raiz e executar o binário diretamente do diretório build/. O Makefile impede a poluição da raiz com arquivos binários intermediários (.o).  
* **Isolamento de Scripts de Apoio e Artefatos de Saída:** A separação de scripts/ e data/ impede que arquivos de dados gerados (.txt) e scripts Python fiquem misturados ao código-fonte em C, garantindo a reprodutibilidade dos gráficos solicitados.

# 4\. Especificação do Design dos Módulos em C

* **Módulo shared\_mem (shared\_mem.h / shared\_mem.c):** Contém a struct SharedBuffer com os vetores u(t) e y\_f(t). Encapsula um pthread\_mutex\_t. Nenhuma variável é acessada diretamente por fora; o acesso ocorre obrigatoriamente pelas funções thread-safe shared\_mem\_write\_u(), shared\_mem\_read\_u(), shared\_mem\_write\_yf() e shared\_mem\_read\_yf().  
* **Módulo timer\_rt (timer\_rt.h / timer\_rt.c):** Controla a periodicidade precisa de 30 ms e 50 ms via clock\_nanosleep() configurado com CLOCK\_MONOTONIC e flag TIMER\_ABSTIME para evitar acúmulo de drift. Computa a métrica instantânea do período T(k) e do jitter J(k).  
* **Módulo telemetry (telemetry.h / telemetry.c \- Thread 1, 30 ms):** Implementa a regra do perfil de entrada u(t). Escreve os dados formatados em data/simulation\_output.txt e acumula estatísticas de tempo real (média, variância, desvio padrão, máximo e mínimo).  
* **Módulo physics (physics.h / physics.c \- Thread 2, 50 ms):** Resolve a integração numérica no espaço de estados para calcular o estado do centro de massa e aplica o deslocamento do diâmetro D \= 0.30 m para calcular o ponto frontal y\_f(t).  
* **Módulo main (main.c):** Instancia o mutex, dispara as duas threads com pthread\_create, aguarda a conclusão dos 20 s de simulação e faz o pthread\_join limpando os recursos do sistema.

🤖 Gostaria que eu forneça uma proposta pronta do arquivo Makefile unificado para essa hierarquia ou o código em C do módulo shared\_mem?  
