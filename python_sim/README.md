# Simulador Visual Interativo 2D — Lab 2 (`python_sim`)

Simulador gráfico em Python (`tkinter` + `numpy`) que desenha o circuito completo em formato de "8" do **Laboratório 2** e permite controlar o avanço e o retorno do robô diferencial pelo teclado.

## Representação Visual
- **Circuito de Fundo:** Permanece visível na tela (trecho azul para $0 \le t < 10\,\text{s}$ no sentido anti-horário e trecho laranja para $10 \le t \le 20\,\text{s}$ no sentido horário).
- **Robô:** Representado por um círculo com uma **bolinha amarela na borda frontal** indicando a frente do robô ao longo da trajetória.

## Como Executar

Dentro do diretório `python_sim/`:

```bash
make
```

O `Makefile` criará automaticamente o ambiente virtual local `python_sim/.venv`, garantirá os dados da simulação e abrirá a janela interativa.

## Controles pelo Teclado

| Tecla | Ação |
| :---: | :--- |
| **`Seta Direita (→)`** | Inicia/avança a trajetória no sentido anti-horário seguindo o Lab 2 ($t: 0 \to 20\,\text{s}$) |
| **`Seta Esquerda (←)`** | Faz o robô voltar pelo circuito no sentido inverso ($t \to 0\,\text{s}$) |
| **`Espaço`** | Pausa ou retoma o movimento |
| **`Seta Cima (↑)` / `Seta Baixo (↓)`** | Aumenta ou diminui a velocidade de reprodução ($0.25\times$ a $8\times$) |
| **`R`** | Reinicia o robô na posição inicial $(0.15, 0.00)\,\text{m}$ em $t = 0\,\text{s}$ |
| **`Q` / `Esc`** | Fecha a simulação |

