# Guia Estrito de Padrões de Codificação em C Embarcado

## Padrão Técnico e Especificação para Automação por IA e Ensino de Engenharia (doc/coding\_standards.md)

# 1\. Visão Geral e Filosofia de Projeto

A engenharia de sistemas embarcados de alta integridade e tempo real exige uma abordagem severamente restritiva em relação ao uso da linguagem de programação C. Em cenários de missão crítica, tais como sistemas aeroespaciais, automotivos (ISO 26262 ASIL-D) e de controle industrial, a imprevisibilidade do código não representa apenas um defeito de software, mas um risco direto e inaceitável à segurança humana e à integridade operacional do equipamento. Nestes domínios, o software de bordo deve operar sob determinismo temporal absoluto e garantia matemática de ausência de falhas em tempo de execução (*runtime crashes*).

A fragilidade da linguagem C padrão decorre de sua especificação formal (ISO/IEC 9899). Conforme fundamentado por Bagnara et al., a norma da linguagem divide intencionalmente certos comportamentos em três categorias não-definidas:

* **Comportamento Indefinido (*Undefined Behavior \- UB*):** No qual o padrão não impõe qualquer requisito, permitindo falhas catastróficas ou corrupção silenciosa de dados.  
* **Comportamento Não-Especificado (*Unspecified Behavior*):** No qual o compilador escolhe entre alternativas válidas sem obrigação de documentar o critério.  
* **Comportamento Definido pela Implementação (*Implementation-Defined Behavior*):** Onde a escolha do compilador é documentada, mas varia entre diferentes arquiteturas e coleções de ferramentas.

A filosofia original do C — sumarizada pelos preceitos "confie no programador", "permita que o programador faça qualquer coisa" e "mantenha a execução rápida, mesmo que não seja portável" — é inerentemente perigosa para aplicações de alta integridade. Compiladores modernos exploram agressivamente o comportamento indefinido sob a "regra do como-se" (*as-if rule*), assumindo que o código nunca violará o padrão. Por exemplo, na verificação de transbordamento de inteiros com sinal como (v \+ 1 \> v), o compilador pode otimizar a expressão removendo a checagem por completo e substituindo-a por um valor constante verdadeiro (1), eliminando a única salvaguarda do sistema contra *overflow*. De forma análoga, operações de deslocamento de bits além da largura do tipo (ex: i \<\< 32 em arquiteturas x86) resultam no mascaramento do contador pelo processador (32 & 0x1F \= 0), transformando o deslocamento em uma instrução nula (*no-op*) sem aviso.

Para eliminar essas vulnerabilidades, este padrão técnico unifica e operacionaliza os quatro pilares normativos da indústria de software crítico:

* **BARR-C:2018:** Focado na clareza visual, formatação inequívoca e redução de erros humanos de interpretação do código.  
* **NASA JPL DOCID D-60411 / Power of Ten:** Projetado para impor extrema simplicidade no fluxo de controle e assegurar a auditabilidade via verificação estática automatizada.  
* **MISRA C:2023 / MISRA C:2025:** Focado na prevenção e eliminação sistemática de comportamentos indefinidos, não-especificados e conversões implícitas inseguras.  
* **AUTOSAR C++14/C:** Orientado ao gerenciamento determinístico de recursos em arquiteturas distribuídas e de tempo real.

A convergência dessas normas estabelece quatro mandatos arquiteturais inegociáveis para qualquer software desenvolvido sob este padrão:

1. **1\. Prevenção Absoluta de Estouro de Pilha (*Stack Overflow*):** Garantia de que a profundidade máxima de chamadas e a alocação de memória local sejam limitadas e prováveis estaticamente antes do *deployment*.  
2. **2\. Eliminação do Não-Determinismo Temporal no Tempo de Execução de Pior Caso (WCET \- *Worst-Case Execution Time*):** Garantia de que a complexidade temporal das rotinas críticas permaneça estritamente delimitada ( \$O(1)\$ ), eliminando latências imprevisíveis.  
3. **3\. Prevenção de Fragmentação de Memória e Vazamentos (*Memory Leaks*):** Proibição de ciclos de alocação/desalocação que possam exaurir a memória operacional durante a execução contínua do sistema.  
4. **4\. Garantia de Zero Falhas em Tempo de Execução (*Runtime Crashes*):** Eliminação de exceções não tratadas, estouros de capacidade e acessos através de ponteiros inválidos.

Esta disciplina rigorosa e determinística começa no controle absoluto da memória física do sistema, conforme especificado na Seção 2\.

# 2\. Gerenciamento Estrito de Memória e Proibição do Heap

O uso do *heap* dinâmico em sistemas de tempo real de alta integridade representa a principal causa de falhas catastróficas imprevisíveis e da degradação do determinismo temporal. Alocadores genéricos de memória dependem intrinsecamente do histórico de solicitações e da ordem de liberação dos blocos, resultando em um estado de fragmentação do *heap* que se altera continuamente ao longo do tempo de operação.

## Mandato de Proibição Absoluta

É expressamente proibida a execução de chamadas a funções de alocação ou desalocação dinâmica de memória — incluindo malloc(), calloc(), realloc(), free(), sbrk() e alloca() — após a fase de inicialização das tarefas do sistema. Este mandato é respaldado formalmente pelas seguintes normas de segurança crítica:

* **JPL Rule 5:** Proíbe estritamente o uso de alocação dinâmica de memória após a inicialização das tarefas (*"There shall be no use of dynamic memory allocation after task initialization"*).  
* **MISRA C:2023 Rule 21.3 / MISRA C:2025 Rule 22.2:** Restringe a utilização de rotinas de alocação do cabeçalho e exige o banimento de liberação dupla (*double-free*) e uso de memória após liberação (*dangling pointers*).  
* **AUTOSAR C++14/C Rule A18-5-1:** Proíbe totalmente a utilização das funções de alocação dinâmica padrão do C durante a fase de execução operacional (*Running Phase*).

## Justificativa Técnica e Física

A alocação dinâmica viola diretamente os requisitos do Tempo de Execução de Pior Caso (WCET). Devido à fragmentação dinâmica da memória, o tempo necessário para que um alocador encontre um bloco contíguo livre não é constante, variando de acordo com o histórico de execução da aplicação. Essa variabilidade impede que ferramentas formais de análise estática derivem um limite superior determinístico ( \$O(1)\$ ) para a execução do código.

Além disso, o uso do *heap* introduz os riscos de exaustão imprevisível de memória em tempo de execução, referências a ponteiros pendentes (*dangling pointers*) e corrupção do mapa de memória por liberação dupla (*double-free*).

Para contornar esse risco, este padrão adota a arquitetura do NASA Core Flight System (cFS) OSAL (*Operating System Abstraction Layer*). Na camada OSAL, todos os recursos do sistema (tarefas, mutexes, filas e *buffers*) são pré-alocados fisicamente em tabelas estáticas de descritores durante a compilação ou na fase de pré-inicialização do sistema de suporte à plataforma (PSP \- *Platform Support Package*). Dessa forma, qualquer falha por exaustão de memória manifesta-se estritamente na fase de *boot*, impedindo falhas de alocação durante a execução do software de bordo.

## Exemplo Prático de Código em C (VIOLAÇÃO vs. SOLUÇÃO)

### Código Não-Conforme (VIOLAÇÃO)

### O código abaixo exemplifica uma rotina de processamento de telemetria que aloca temporariamente um *buffer* no *heap* durante a execução do ciclo de controle de tempo real:

```c
/* VIOLACAO: Uso de alocacao dinamica no heap dentro de tarefa de tempo real */
#include <stdlib.h>
#include <stdint.h>

void process_telemetry_data(const uint8_t *p_raw_stream, uint16_t stream_length) {
    /* Infracao: malloc() aloca memoria no heap em tempo de execucao */
    uint8_t *p_working_buffer = (uint8_t *)malloc(stream_length * sizeof(uint8_t));
    if (p_working_buffer == NULL) {
        /* Tratamento de falha dinamico e imprevisivel */
        return;
    }
    for (uint16_t i = 0u; i < stream_length; i++) {
        p_working_buffer[i] = p_raw_stream[i] ^ 0xFFu;
    }
    /* Processa os dados... */
    /* Infracao: Risco de memory leak ou ponteiro pendente se omitido */
    free(p_working_buffer);
}
```

### Código Conforme (SOLUÇÃO)

A solução abaixo substitui a alocação dinâmica por uma estrutura de *pool* de memória estático pré-alocado, gerenciando o estado de alocação de forma determinística \$O(1)\$ e sem fragmentação:

```c
/* SOLUCAO: Pool de memoria estatico pre-alocado garantindo O(1) e determinismo */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define MAX_STREAM_SIZE (256u)

typedef struct {
    uint8_t buffer_storage[MAX_STREAM_SIZE];
    bool is_allocated;
} static_buffer_pool_t;

/* Pool pre-alocado estaticamente no escopo do arquivo */
static static_buffer_pool_t g_telemetry_pool = { .is_allocated = false };

void process_telemetry_data_safe(const uint8_t *p_raw_stream, uint16_t stream_length) {
    /* Garante limites estaticos e validacao sem recorrer ao heap */
    if ((p_raw_stream == NULL) || (stream_length == 0u) || (stream_length > MAX_STREAM_SIZE)) {
        return;
    }
    /* Controle deterministico de alocacao estatica */
    if (g_telemetry_pool.is_allocated) {
        /* Recurso ocupado: tratamento defensivo O(1) */
        return;
    }
    g_telemetry_pool.is_allocated = true;
    /* Operacao O(1) utilizando recurso totalmente estatico */
    for (uint16_t i = 0u; i < stream_length; i++) {
        g_telemetry_pool.buffer_storage[i] = p_raw_stream[i] ^ 0xFFu;
    }
    /* Libera o pool estatico apos o processamento seguro */
    g_telemetry_pool.is_allocated = false;
}
```

A estabilidade proporcionada pelo gerenciamento estático de memória depende diretamente do rigor utilizado na representação dos dados e na especificação da largura dos tipos, conforme detalhado na Seção 3\.

# 3\. Tipagem de Alta Integridade e Largura Fixa (\<stdint.h\>)

A utilização de tipos inteiros primitivos da linguagem C padrão (como int, short, long) em sistemas embarcados cria ambiguidades severas, pois a largura em bits desses tipos varia dependendo da arquitetura do processador (16, 32 ou 64 bits) e do modelo de dados do compilador (ex: ILP32 vs. LP64). Essa variação pode causar estouros imprevisíveis de capacidade (*overflow*) e comportamentos dependentes da implementação ao migrar o código entre plataformas.

## Tipagem Estrita Obligatória

É obrigatório o mapeamento exclusivo de tipos inteiros com sinal e largura explicitamente definidos através do cabeçalho estandardizado \<stdint.h\>, bem como o uso de tipos booleanos definidos em \<stdbool.h\>:

* **Tipos Permitidos:** uint8\_t, int8\_t, uint16\_t, int16\_t, uint32\_t, int32\_t, uint64\_t, int64\_t, e bool.  
* **Proibição de Tipos Ambíguos:** O uso isolado de short, long ou int é terminantemente proibido.  
* **Uso Restrito de char:** O uso do tipo primitivo char é permitido única e exclusivamente para a representação de literais de caracteres legíveis e cadeias de texto (*strings*). Para qualquer manipulação numérica ou de *bytes* de 8 bits, deve-se usar estritamente uint8\_t ou int8\_t.

Esta regra é amparada normativamente por:

* **BARR-C 5.2:** Exige o uso explícito de tipos com largura fixa definidos pela norma ISO C99.  
* **JPL Rule 17:** Determina a substituição de tipos de dados pré-definidos do C por abstrações que explicitem o tamanho e o sinal (ex: U32, I16, uint32\_t).  
* **AUTOSAR C++14/C Rule A3-9-1:** Bane o uso de tipos fundamentais do C quando existirem equivalentes de largura fixa em \<stdint.h\>.

## Regras para Literais e Conversões Implícitas

Para conter reinterpretações acidentais e conversões implícitas de tipo (*implicit type casting*):

1. **1\. Sufixos Numéricos Explícitos e Válidos em C99:** Todas as constantes literais numéricas devem obrigatoriamente declarar seu tipo e sinal através de sufixos numéricos explícitos compatíveis com a norma ISO C99 (ex: 100u ou 100U para uint32\_t/uint16\_t, 1000L ou (int32\_t)1000 para int32\_t, 0.15f para ponto flutuante de precisão simples). Sufixos não estandardizados por C99 (como 1000i32) são **estritamente proibidos**, pois violam a compilação \-std=c99 \-pedantic \-Werror.  
2. **2\. Proibição de Conversões Implícitas:** São proibidas conversões implícitas de tipos que possam resultar em perda de precisão, alteração de sinal ou truncamento. Caso uma conversão seja estritamente necessária, ela deve ser promovida de forma explícita via *cast* validado e auditável.

## Exemplo Prático de Código em C (VIOLAÇÃO vs. SOLUÇÃO)

### Código Não-Conforme (VIOLAÇÃO)

O código a seguir utiliza tipos nativos ambíguos, literais sem sufixo e realiza operações de deslocamento de bits (*shift*) vulneráveis a *overflow* e comportamento indefinido:

```c
/* VIOLACAO: Tipos nativos ambiguos, sem sufixos e conversao implicita */
int calculate_encoder_ticks(int raw_value, long offset) {
    /* Infracao: Uso de 'int' e 'long' cujas larguras variam por arquitetura */
    /* Infracao: Literal '1000' sem sufixo numerico explicito */
    /* Infracao: Shift de bits em tipo signed pode gerar undefined behavior */
    int scaled_value = (raw_value << 4) + 1000;
    /* Infracao: Conversao implicita de 'long' para 'int' com perda de precisao */
    int final_ticks = scaled_value + offset;
    return final_ticks;
}
```

### Código Conforme (SOLUÇÃO)

A versão reescrita garante portabilidade estrita ISO C99, prevenção de *overflow* e clareza de tipos conforme as normas:

```c
/* SOLUCAO: Tipagem fixa com <stdint.h>, sufixos C99 validos e casts explicitos */
#include <stdint.h>

int32_t calculate_encoder_ticks_safe(int32_t raw_value, int32_t offset) {
    /* Uso explicito de tipos de largura fixa e constantes C99 validas */
    const int32_t scale_factor = (int32_t)1000;
    /* Prevencao de overflow com multiplicacao explicita em vez de shift signed */
    int32_t scaled_value = (raw_value * (int32_t)16) + scale_factor;
    /* Operacao sem conversao implicita insegura */
    int32_t final_ticks = scaled_value + offset;
    return final_ticks;
}
```

A precisão dos tipos de dados estabelece a base necessária para garantir o controle determinístico do fluxo de execução do programa, como abordado na Seção 4\.

# 4\. Controle de Fluxo Simplificado e Determinismo Temporal

O determinismo temporal de um sistema de tempo real exige uma topologia de código cujos caminhos de execução sejam finitos, transparentes e completamente auditáveis por ferramentas de análise estática antes da implantação (*deployment*).

## Banimento Absoluto de Recursão

É terminantemente proibido o uso de recursão, seja ela direta (uma função chamando a si mesma) ou indireta (uma função \$A\$ chamando \$B\$, que por sua vez chama \$A\$).

* **Fundamentação Normativa:** **JPL Rule 4** (*"There shall be no direct or indirect use of recursive function calls"*) e **MISRA C:2023 Rule 17.2**.  
* **Justificativa Técnica:** A ausência de recursão garante um Grafo de Chamadas Acíclico (DAG \- *Directed Acyclic Graph*). Essa topologia simplificada permite que analisadores estáticos de código calculem com precisão matemática a profundidade máxima da pilha de execução (*stack depth*), provando a impossibilidade de ocorrência de *stack overflow* durante a operação do sistema.

## Limites Estáticos de Repetição e Regra de Exceção

Todas as estruturas de repetição (for, while, do-while) devem possuir um limite estático superior provável em tempo de compilação (**JPL Rule 3**). Ferramentas de análise estática devem ser capazes de afirmar a existência desse limite superior para validar o WCET da rotina.

* **Mecanismo de Salvaguarda:** Loops que percorrem estruturas dinâmicas ou contadores de *hardware* devem incluir um limite máximo de contagem (*timeout counter*). Se este limite for excedido, a repetição deve ser interrompida e uma falha deve ser registrada.  
* **Exceção do Loop Servidor Principal:** A única exceção admitida a esta regra é o loop principal do servidor ou da tarefa (*task main loop*), responsável pelo processamento contínuo de eventos. Este loop não-terminativo específico deve obrigatoriamente conter a anotação em formato de comentário C: /\* @non-terminating@ \*/

## Proibição de Desvios Incondicionais

São expressamente banidas as instruções de desvio incondicional goto, bem como os saltos não-locais setjmp() e longjmp() (**JPL Rule 11**, **BARR-C 8.5**, **MISRA C:2023 Rule 14.4**). Tais instruções destroem a estruturação do código, impedem a verificação formal do fluxo de controle e introduzem complexidade desnecessária na análise de integridade.

## Exemplo Prático de Código em C (VIOLAÇÃO vs. SOLUÇÃO)

### Código Não-Conforme (VIOLAÇÃO)

Abaixo, ilustra-se uma rotina de varredura que utiliza recursão direta, loop indeterminado e desvio goto:

```c
/* VIOLACAO: Recursao, loop sem limite provavel e instrucao goto */
#include <stdint.h>

uint32_t search_node_recursive(uint32_t current_id, uint32_t target_id) {
    if (current_id == target_id) {
        goto NODE_FOUND; /* Infracao: Uso de goto destruindo fluxo estruturado */
    }
    if (current_id > target_id) {
        /* Infracao: Recursao direta. Impede determinismo da pilha de chamada */
        return search_node_recursive(current_id - 1u, target_id);
    }
NODE_FOUND:
    return current_id;
}

void wait_hardware_ready(volatile uint8_t *p_status_reg) {
    /* Infracao: Loop while sem limite estatico determinavel (risco de trava) */
    while ((*p_status_reg & 0x01u) == 0u) {
        /* Aguarda indefinidamente */
    }
}
```

### Código Conforme (SOLUÇÃO)

A reconstrução do código elimina a recursão em favor de iteração com limites estáticos comprováveis e adiciona *timeout* de segurança para a verificação de *hardware*:

```c
/* SOLUCAO: Iteracao deterministica, limites estaticos e ausência de desvios */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#define MAX_SEARCH_ITERATIONS (1000u)
#define HARDWARE_TIMEOUT_CYCLES (10000u)

uint32_t search_node_iterative_safe(uint32_t start_id, uint32_t target_id) {
    uint32_t current_id = start_id;
    uint32_t iterations = 0u;
    /* Loop com limite estatico rigoroso provavel por ferramentas estaticas */
    while ((current_id > target_id) && (iterations < MAX_SEARCH_ITERATIONS)) {
        current_id--;
        iterations++;
    }
    return current_id;
}

bool wait_hardware_ready_safe(volatile const uint8_t *p_status_reg) {
    uint32_t timeout_counter = 0u;
    bool is_ready = false;
    if (p_status_reg == NULL) {
        return false;
    }
    /* Loop iterativo com limite superior explicito contra travamento de CPU */
    for (timeout_counter = 0u; timeout_counter < HARDWARE_TIMEOUT_CYCLES; timeout_counter++) {
        if ((*p_status_reg & 0x01u) != 0u) {
            is_ready = true;
            break; /* Saida estruturada antecipada autorizada */
        }
    }
    return is_ready;
}
```

Um fluxo de controle previsível fornece a base necessária para a aplicação de verificações ativas e programação defensiva em tempo de execução, assunto abordado na Seção 5\.

# 5\. Programação Defensiva, Assertions e Invariantes

A arquitetura de software de alta integridade exige a adoção do princípio das "funções totais". Uma função total é aquela projetada para responder de maneira segura e previsível a qualquer combinação de parâmetros de entrada, eliminando cenários de execução não mapeados e contendo eventuais falhas no módulo onde elas se originam.

## Validação de Parâmetros de Entrada

Todos os parâmetros passados para funções públicas ou de interface de módulo (APIs) devem ser rigorosamente validados quanto à sanidade antes da execução da lógica operacional (**JPL Rule 15**):

* **Sanidade de Ponteiros:** Verificar obrigatoriamente se os ponteiros recebidos são diferentes de NULL.  
* **Sanidade de Intervalo:** Verificar se valores numéricos estão estritamente contidos nos intervalos operacionais esperados (*range checking*).

## Uso de Assertions e Mecanismo de Invariantes

Deve-se incorporar o uso sistemático de verificações de sanidade por meio do padrão de macro pura c\_assert (**JPL Rule 16**):  
**1\. Estrutura Canônica da Macro Pura:** Em conformidade estrita com a regra JPL Rule 16, a macro de *assertion* deve ser definida no formato booleano puro sem envolver invocações por funções invólucro que mascarem a avaliação:

```c
#define c_assert(e) ((e) ? (true) : (log_assertion_failure(__FILE__, __LINE__, #e), false))
```

1. **2\. Isenção de Efeitos Colaterais:** As declarações contidas em uma *assertion* devem obrigatoriamente ser livres de efeitos colaterais. Uma *assertion* jamais deve alterar o estado do sistema (ex: proíbe-se c\_assert(x++)).  
2. **3\. Rastreabilidade e Logs:** Em ambiente de desenvolvimento e teste, a falha em uma *assertion* deve capturar e registrar os identificadores de contexto pré-definidos pelo pré-processador: \_\_FILE\_\_ (nome do arquivo) e \_\_LINE\_\_ (número da linha), convertendo a condição em uma cadeia de texto via operador \#.  
3. **4\. Ação de Recuperação em Voo:** Em código de voo/produção, a falha em uma *assertion* não deve travar o processador em um loop infinito. Ela deve acionar uma ação de recuperação limpa e previsível (ex: retornar um código de erro do módulo) e registrar o evento em um log seguro de diagnóstico.

## Tratamento Obrigatório de Retornos

Os valores de retorno de todas as funções não-void devem ser obrigatoriamente verificados e tratados pela função chamadora (**NASA SWE-061**, **JPL Rule 14**, **MISRA C:2023 Rule 16.10**). Caso o valor de retorno de uma função deva ser intencionalmente ignorado, a chamada deve ser precedida por um *cast* explícito para (void).

## Exemplo Prático de Código em C (VIOLAÇÃO vs. SOLUÇÃO)

### Código Não-Conforme (VIOLAÇÃO)

O código abaixo desconsidera a validação de parâmetros, executa expressões com efeitos colaterais em *assertions* e ignora o retorno de funções críticas:

```c
/* VIOLACAO: Desprezo por validacao, efeito colateral em assertion e retorno ignorado */
#include <stdint.h>
#include <assert.h>

int32_t write_sensor_data(uint8_t *p_buffer, int32_t value) {
    /* Infracao: Nenhuma verificacao de p_buffer NULL antes do acesso */
    /* Infracao: Efeito colateral inside assert modifica o estado operacional */
    assert(value++ > 0);
    *p_buffer = (uint8_t)value;
    return 0;
}

void system_process(uint8_t *p_data) {
    /* Infracao: Retorno de funcao nao-void totalmente ignorado */
    write_sensor_data(p_data, 50);
}
```

### Código Conforme (SOLUÇÃO)

A reconstrução aplica programação defensiva estrita, validação total de entradas, macro c\_assert pura sem efeitos colaterais e tratamento dos códigos de retorno:

```c
/* SOLUCAO: Programacao defensiva, assertions puras e tratamento de retornos */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

typedef enum {
    RESULT_OK = 0,
    RESULT_ERROR_NULL_POINTER,
    RESULT_ERROR_INVALID_PARAM
} result_code_t;

static void log_assertion_failure(const char *p_file, int32_t line, const char *p_expr) {
    /* Grava os dados de contexto no log de diagnostico do sistema */
    (void)p_file;
    (void)line;
    (void)p_expr;
}

/* Macro canonica do JPL Rule 16: booleana, pura e sem efeitos colaterais */
#define c_assert(e) ((e) ? (true) : (log_assertion_failure(__FILE__, __LINE__, #e), false))

result_code_t write_sensor_data_safe(uint8_t *p_buffer, int32_t value) {
    /* 1. Validacao de parametros de entrada (Funcao Total) */
    if (p_buffer == NULL) {
        return RESULT_ERROR_NULL_POINTER;
    }
    if ((value < 0) || (value > 255)) {
        return RESULT_ERROR_INVALID_PARAM;
    }
    /* 2. Sanidade via assertion pura do JPL Rule 16 */
    if (!c_assert(value <= 255)) {
        return RESULT_ERROR_INVALID_PARAM;
    }
    *p_buffer = (uint8_t)value;
    return RESULT_OK;
}

void system_process_safe(uint8_t *p_data) {
    /* 3. Tratamento explicito e obrigatorio do valor de retorno */
    result_code_t status = write_sensor_data_safe(p_data, 50);
    if (status != RESULT_OK) {
        /* Acao de recuperacao limpa e segura */
    }
}
```

A disciplina defensiva é complementada pelo isolamento do estado do software por meio de uma estrutura modular estrita, discutida na Seção 6\.

# 6\. Modularidade, Ocultação de Dados e Escopo

A minimização do escopo e a ocultação de dados (*data hiding*) são vitais para evitar acoplamentos indevidos entre componentes do software e mitigar os riscos de corrupção não intencional do estado global do sistema.

## Minimização de Escopo e Encapsulamento

Variáveis e dados devem ser declarados no menor nível de escopo possível (**JPL Rule 13**, **Power of Ten Rule 6**, **MISRA C:2023 Rule 8.7**):

* **Linkage Interna Obligatória:** Todas as variáveis e funções com escopo de arquivo que não precisem ser acessadas fora do próprio módulo devem ser obrigatoriamente qualificadas com o especificador static (*internal linkage*). Esta medida encapsula os símbolos, evitando a exposição e alteração inadvertida do estado interno por outros módulos.  
* **Uso de Declarações extern:** Declarações extern devem ser evitadas ao máximo. Quando estritamente necessárias, devem ser localizadas exclusivamente dentro de arquivos de cabeçalho (.h), que por sua vez devem ser incluídos tanto no arquivo fonte de definição quanto nos arquivos de consumo, permitindo que o compilador valide a consistência dos tipos.

## Restrição Restrita de Indireção de Ponteiros

Enquanto o padrão JPL D-60411 (Rule 26/27) permite historicamente até dois níveis de indireção (T \*\*ptr), este padrão técnico **estreita deliberadamente a restrição para no máximo 1 nível de indireção (**\*T ptr**)**:

1. **1\. Limite Estrito de Indireção (1 Nível):** A declaração e desreferenciação de ponteiros são limitadas a no máximo 1 nível (T \*ptr). O uso de ponteiros para ponteiros (T \*\*ptr) é terminantemente proibido para simplificar a análise de aliasing e garantir a verificação formal de memória por ferramentas estáticas.  
2. **2\. Ponteiros de Função:** É proibido o uso de ponteiros de função não-constantes e não-autenticados (**JPL Rule 29**). Se o uso de ponteiros de função for inevitável, eles devem ser declarados como constantes (const) e inicializados estaticamente para garantir que o fluxo de controle permaneça transparente e acíclico.

## Imutabilidade com const

O qualificador const deve ser aplicado de forma sistemática e abrangente (**JPL Rule 13**). Todos os parâmetros de função passados por referência (ponteiros) que sejam destinados estritamente à leitura devem ser qualificados como ponteiros para dados constantes (ex: const uint8\_t \* const p\_data).

## Exemplo Prático de Código em C (VIOLAÇÃO vs. SOLUÇÃO)

### Código Não-Conforme (VIOLAÇÃO)

O exemplo a seguir expõe dados do módulo globalmente, utiliza indireção dupla de ponteiros e omite a qualificação de imutabilidade const:

```c
/* VIOLACAO: Variavel global exposta, dupla indirecao e falta de const */
#include <stdint.h>

/* Infracao: Variavel global sem static (visivel globalmente, risco de corrupcao) */
uint32_t system_state_counter = 0;

/* Infracao: Nivel de indirecao duplo (int **), violando o limite do padrao */
void update_data_pointer(uint32_t **pp_data_ptr, uint32_t *p_new_val) {
    /* Infracao: Falta do qualificador const no ponteiro de leitura p_new_val */
    if (pp_data_ptr != 0) {
        **pp_data_ptr = *p_new_val;
    }
}
```

### Código Conforme (SOLUÇÃO)

O código foi refatorado para garantir o encapsulamento estático dos dados, limite de indireção simples (1 nível) e imutabilidade dos dados de entrada:

```c
/* SOLUCAO: Encapsulamento estatico, indirecao simples (1 nivel) e imutabilidade */
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Encapsulamento estrito no escopo do arquivo via especificador static */
static uint32_t g_system_state_counter = 0u;

/* Indirecao simples estrita (1 nivel) e parametro de leitura protegido por const */
bool update_data_value_safe(uint32_t *p_target_data, const uint32_t * const p_new_val) {
    if ((p_target_data == NULL) || (p_new_val == NULL)) {
        return false;
    }
    *p_target_data = *p_new_val;
    g_system_state_counter++;
    return true;
}
```

O encapsulamento do código relaciona-se diretamente com as diretrizes de formatação, nomenclatura e com as rigorosas opções de compilação detalhadas na Seção 7\.

# 7\. Formatação, Nomenclatura e Opções de Compilação (BARR-C:2018)

A consistência visual e a severidade nas configurações do compilador formam a primeira linha de defesa contra erros humanos, ambiguidades sintáticas e desvios das diretrizes do projeto.

## Padrão de Nomenclatura e Estilo (BARR-C:2018)

A formatação do código deve ser perfeitamente uniforme e seguir os padrões estabelecidos pela BARR-C:2018:

* **Sintaxe de Variáveis e Funções:** Uso exclusivo de *snake\_case* para nomes de variáveis, parâmetros e funções (ex: calculate\_checksum, p\_data\_buffer).  
* **Sufixo para Tipos Definidos:** Sufixo \_t obrigatório para declaração de estruturas (struct), enumerações (enum) e definições de tipo (typedef) (ex: telemetry\_packet\_t).  
* **Prefixos de Escopo e Tipo:** Prefixo g\_ obrigatório para variáveis estáticas globais ou de escopo de arquivo (ex: g\_system\_state), e prefixo p\_ para variáveis que sejam ponteiros (ex: p\_payload).  
* **Limite de Largura de Linha:** Limite estrito de largura de linha de no máximo **80 caracteres** (**BARR-C 1.2**). Código que ultrapassar esse limite deve ser quebrado de forma legível em linhas subsequentes.  
* **Instrução Única por Linha:** Nenhuma linha de texto deve conter mais de uma instrução ou declaração de variável (**JPL Rule 24**).

## Configuração Estrita do Compilador (Zero Warnings)

Em estrita conformidade com a **JPL Rule 2**, todo o código deve ser compilado com todos os avisos (*warnings*) do compilador ativados no nível máximo disponível. Todos os avisos emitidos pelo compilador devem ser tratados estritamente como erros de compilação, interrompendo o processo de *build* até que sejam devidamente corrigidos.

Abaixo é transcrito o bloco exato de opções do compilador GCC que deve ser incluído no Makefile do projeto:

```
# Flags do Compilador GCC para Verificacao Estrita de Alta Integridade
CFLAGS += -Wall
CFLAGS += -Wextra
CFLAGS += -Werror
CFLAGS += -pedantic
CFLAGS += -std=c99
CFLAGS += -Wshadow
CFLAGS += -Wpointer-arith
CFLAGS += -Wcast-qual
CFLAGS += -Wcast-align
CFLAGS += -Wstrict-prototypes
CFLAGS += -Wmissing-prototypes
CFLAGS += -Wconversion
```

A combinação destas regras de compilação, formatação e arquitetura forma a especificação técnica completa a ser operacionalizada pelo agente de IA no ecossistema Google Antigravity, conforme definido na Seção 8\.

# 8\. Prompt Rule Card para Ingestão no Google Antigravity

Abaixo é apresentado o *Rule Card* sintético, compacto e diretamente executável por máquina, projetado para ingestão imediata e aplicação por agentes de Inteligência Artificial (como Gemini 3.8 Flash) operando no ambiente Google Antigravity.

```
# ANTIGRAVITY AGENT DIRECTIVE: EMBEDDED C STRICT CODING STANDARD
## CORE MANDATES
1. MEMORY: ZERO DYNAMIC ALLOCATION (malloc/free/alloca banned). Use static pre-allocated arrays/pools.
2. TYPES: Use ONLY explicit types (uint8_t, int32_t) and <stdint.h>. Banned: short, long, plain char (except text strings). Always add literal suffixes (e.g., 100u, 0.5f).
3. FLOW CONTROL: NO RECURSION. NO goto/setjmp/longjmp. All loops MUST have provable static upper bounds. Exceptions: main task server loops tagged with /* @non-terminating@ */.
4. DEFENSIVE: Validate ALL public function arguments (check NULL, ranges). Check ALL non-void return values. Use side-effect-free assertions (c_assert) with __FILE__ and __LINE__.
5. SCOPE & POINTERS: Maximum 1 level of pointer indirection (T *ptr). Maximize `static` for file-scope data/functions. Use `const` for read-only parameters.
6. STYLE: Follow BARR-C:2018 (snake_case, typedef ending with _t, pointer prefix p_). Hard wrap at 80 columns.
7. COMPILER: Code must pass zero-warning build with `-Wall -Wextra -Werror -pedantic -std=c99`.
## CODE REFACTORING AND GENERATION ACTION
When generating or reviewing code, ALWAYS generate dual blocks:
- VIOLATION: Show non-compliant code.
- SOLUTION: Provide fully compliant, mission-critical safe code.
```

