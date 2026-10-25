Nesse projeto estamos simulando o **computador de navegação autônoma de um veículo (Thread 1\)** enviando ordens de manobra para a **dinâmica física e sensorial do veículo (Thread 2\)** cumprir uma rota programada em formato de "S".

objetivo: fazer um S

A relação entre a **Thread 1** e a **Thread 2** é de **Produtor e Consumidor Cruzado (Duplo Produtor-Consumidor)** operando em um sistema **assíncrono e multi-taxa (multi-rate)**.

Aqui está exatamente como elas se relacionam na prática:

## **1\. O Fluxo de Dados Cruzado**

As duas threads conversam continuamente através da memória compartilhada:

* 

```
                 ┌────────────────────────┐
                  │        THREAD 1        │
                  │   Piloto / Telemetria  │
                  │     (Período: 30ms)    │
                  └───────────┬────────────┘
                              │
  Escreve u(t) = [v, ω]^T     │     Lê y(t) = [y_x, y_y, θ]^T
  (Comandos de Velocidade)    │     (Posição Atual do Robô)
                              ▼
        ═══════════════════════════════════════════
                   MEMÓRIA COMPARTILHADA
        ═══════════════════════════════════════════
                              ▲
  Lê u(t) = [v, ω]^T          │     Escreve y(t) = [y_x, y_y, θ]^T
  (Comandos de Velocidade)    │     (Posição Atual do Robô)
                              │
                  ┌───────────┴────────────┐
                  │        THREAD 2        │
                  │    Motor de Física     │
                  │     (Período: 50ms)    │
                  └────────────────────────┘
```

* **Da Thread 1 para a Thread 2:** A Thread 1 define e entrega a intenção de movimento $u(t)=[v,\omega {]}^{T}$ (velocidade linear e angular).  
* **Da Thread 2 para a Thread 1:** A Thread 2 processa a física, calcula onde o robô foi parar e devolve a posição atualizada da frente do robô $y(t)$.

## **2\. A Dinâmica Temporal (Descompasso de Frequência)**

A relação **não é de "passo e espera"** (uma não fica travada esperando a outra responder para dar o próximo passo). Elas são totalmente **independentes no tempo**:

* A **Thread 1** acorda a cada **30 ms**. Ela pega o último $y(t)$ que estiver disponível na memória, salva no arquivo `.txt` e atualiza a velocidade $u(t)$.  
* A **Thread 2** acorda a cada **50 ms**. Ela pega o último $u(t)$ que estiver na memória, faz as contas trigonométricas da física e atualiza o novo $y(t)$.

Como os tempos são diferentes (30 ms vs 50 ms):

* Às vezes, a Thread 1 vai ler o mesmo $y(t)$ mais de uma vez (porque a Thread 2 ainda não teve tempo de rodar de novo).  
* Em outros momentos, a Thread 2 usará o mesmo comando $u(t)$ em ciclos seguidos (até que a Thread 1 mude o perfil de curva).

## **3\. O Ponto de Conflito (A Memória Compartilhada)**

Como elas tentam acessar a mesma memória em momentos não sincronizados, pode acontecer de a Thread 1 tentar ler a posição $y(t)$ no **exato milissegundo** em que a Thread 2 está no meio do cálculo escrevendo os valores.

É por isso que essa relação exige um **mecanismo de proteção** (uma "trava" ou *mutex*), para garantir que nem o piloto leia dados corrompidos nem a física receba um comando cortado pela metade.

🤖 Quer ver como implementar a estrutura de dados compartilhada em C com as variáveis $u(t)$ e $y(t)$ para essa comunicação?

