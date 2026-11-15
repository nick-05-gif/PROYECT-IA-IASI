# Connect 4 — Monte Carlo Tree Search (MCTS) Experimentation Tool

Visual experimentation tool built in Python to analyze the behavior, convergence, and computational performance of the standard **Monte Carlo Tree Search (MCTS)** algorithm with UCB1 in Connect 4[cite: 18].

**Author:** Rubén Martínez Martínez[cite: 18]  
**Course:** Artificial Intelligence — Gheorghe Asachi Technical University of Iași (TUIASI)[cite: 18]

## Features
- **Board & MCTS Inspector:** Play Human vs. MCTS AI while adjusting the number of simulations per turn ($N$) and the UCB1 exploration constant ($C$) in real time[cite: 18]. Displays dynamic per-column win-rate bars, visit counts, expanded nodes, decision latency, and a chronological round-by-round match log[cite: 18].
- **Experimentation Lab:** Run automated batch benchmarks to evaluate simulation scaling ($N$) against a Random Agent or a Baseline MCTS opponent, as well as head-to-head matchups between custom parameter configurations, exporting comparative Matplotlib charts to PNG (`results/`)[cite: 18].

## Project Structure
- `src/board.py`: Connect 4 rules, gravity mechanics, state cloning, and directional win detection[cite: 18].
- `src/mcts.py`: Standard MCTS implementation (UCB1 Selection, Expansion, Random Playout, Backpropagation)[cite: 18].
- `src/experimenter.py`: Automated alternating-turn match runner and metric aggregator[cite: 18].
- `src/app.py`: Graphical user interface built with CustomTkinter and Matplotlib[cite: 18].
- `main.py`: Application entry point[cite: 18].
- `results/`: Exported PNG charts from experimental runs[cite: 18].

## Installation & Execution
1. Install dependencies:
   ```bash
   pip install -r requirements.txt

2. Launch the application:
    Bash
    python main.py