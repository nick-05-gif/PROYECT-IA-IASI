import random
import time

try:
    from src.board import Connect4Board
    from src.mcts import MCTS
except ImportError:
    from board import Connect4Board
    from mcts import MCTS


class RandomAgent:
    """Agente base que tira al azar. Sirve como referencia para medir cuánto mejora MCTS."""

    def __init__(self):
        self.name = "Random"

    def choose_move(self, board):
        valid_moves = board.get_valid_moves()
        if not valid_moves:
            return None, {"elapsed_time_ms": 0.0, "nodes_created": 0}
        return random.choice(valid_moves), {"elapsed_time_ms": 0.0, "nodes_created": 0}


class MCTSAgent:
    """Envoltorio para usar MCTS dentro del simulador de partidas."""

    def __init__(self, simulations=300, exploration_constant=1.414, label=None):
        self.simulations = simulations
        self.exploration_constant = exploration_constant
        self.engine = MCTS(simulations=simulations, exploration_constant=exploration_constant)
        self.name = label or f"MCTS (N={simulations}, C={exploration_constant})"

    def choose_move(self, board):
        return self.engine.search(board)


def build_agent(config):
    if config["type"] == "random":
        return RandomAgent()
    return MCTSAgent(
        simulations=config.get("simulations", 300),
        exploration_constant=config.get("c", 1.414),
        label=config.get("label"),
    )


def run_matchup(agent_a_cfg, agent_b_cfg, num_games=20, progress_callback=None):
    """
    Enfrenta dos configuraciones durante N partidas.
    Alternamos quién empieza en cada partida porque en Conecta 4 el primer jugador tiene ventaja.
    """
    agent_a = build_agent(agent_a_cfg)
    agent_b = build_agent(agent_b_cfg)

    stats = {
        "agent_a_name": agent_a.name,
        "agent_b_name": agent_b.name,
        "games": num_games,
        "a_wins": 0,
        "b_wins": 0,
        "draws": 0,
        "a_times_ms": [],
        "b_times_ms": [],
        "a_nodes": [],
        "b_nodes": [],
        "game_lengths": [],
    }

    for game_idx in range(num_games):
        board = Connect4Board()

        # En partidas pares empieza A (ficha 1); en impares empieza B (ficha 1)
        if game_idx % 2 == 0:
            p1_agent, p2_agent = agent_a, agent_b
            p1_is_a = True
        else:
            p1_agent, p2_agent = agent_b, agent_a
            p1_is_a = False

        while not board.is_terminal():
            current_agent = p1_agent if board.current_player == Connect4Board.PLAYER_1 else p2_agent
            is_agent_a = (board.current_player == Connect4Board.PLAYER_1 and p1_is_a) or (
                board.current_player == Connect4Board.PLAYER_2 and not p1_is_a
            )

            move, metrics = current_agent.choose_move(board)
            board.make_move(move)

            if is_agent_a:
                stats["a_times_ms"].append(metrics.get("elapsed_time_ms", 0.0))
                stats["a_nodes"].append(metrics.get("nodes_created", 0))
            else:
                stats["b_times_ms"].append(metrics.get("elapsed_time_ms", 0.0))
                stats["b_nodes"].append(metrics.get("nodes_created", 0))

        stats["game_lengths"].append(board.moves_count)

        if board.winner == 0:
            stats["draws"] += 1
        elif (board.winner == Connect4Board.PLAYER_1 and p1_is_a) or (
            board.winner == Connect4Board.PLAYER_2 and not p1_is_a
        ):
            stats["a_wins"] += 1
        else:
            stats["b_wins"] += 1

        if progress_callback:
            progress_callback((game_idx + 1) / num_games)

    stats["a_win_rate"] = round((stats["a_wins"] / num_games) * 100, 1)
    stats["b_win_rate"] = round((stats["b_wins"] / num_games) * 100, 1)
    stats["draw_rate"] = round((stats["draws"] / num_games) * 100, 1)
    stats["a_avg_time_ms"] = round(sum(stats["a_times_ms"]) / max(1, len(stats["a_times_ms"])), 2)
    stats["b_avg_time_ms"] = round(sum(stats["b_times_ms"]) / max(1, len(stats["b_times_ms"])), 2)
    stats["a_avg_nodes"] = round(sum(stats["a_nodes"]) / max(1, len(stats["a_nodes"])), 1)
    stats["b_avg_nodes"] = round(sum(stats["b_nodes"]) / max(1, len(stats["b_nodes"])), 1)
    stats["avg_moves"] = round(sum(stats["game_lengths"]) / max(1, len(stats["game_lengths"])), 1)

    return stats


def run_simulation_scaling(sim_list, games_per_level=16, c_param=1.414, opponent_cfg=None, progress_callback=None):
    """
    Evalúa cómo cambian el % de victorias y el tiempo por jugada al aumentar las simulaciones.
    """
    if opponent_cfg is None:
        opponent_cfg = {"type": "random"}

    results = []
    total_steps = len(sim_list) * games_per_level
    completed_steps = 0

    for sims in sim_list:
        agent_cfg = {"type": "mcts", "simulations": sims, "c": c_param}

        def step_cb(local_progress, base=completed_steps):
            if progress_callback:
                current = base + (local_progress * games_per_level)
                progress_callback(min(1.0, current / total_steps))

        match_stats = run_matchup(agent_cfg, opponent_cfg, num_games=games_per_level, progress_callback=step_cb)
        completed_steps += games_per_level

        results.append(
            {
                "simulations": sims,
                "win_rate": match_stats["a_win_rate"],
                "draw_rate": match_stats["draw_rate"],
                "loss_rate": match_stats["b_win_rate"],
                "avg_time_ms": match_stats["a_avg_time_ms"],
                "avg_nodes": match_stats["a_avg_nodes"],
            }
        )

    return results


if __name__ == "__main__":
    print("Lanzando prueba rápida de escalado de simulaciones (50 vs 250 sims frente a Random)...")
    t0 = time.perf_counter()
    scaling = run_simulation_scaling([50, 250], games_per_level=10)
    for row in scaling:
        print(
            f"Simulaciones: {row['simulations']:>3} | "
            f"Victorias: {row['win_rate']:>5}% | "
            f"Tiempo medio/jugada: {row['avg_time_ms']:>6} ms | "
            f"Nodos medios: {row['avg_nodes']}"
        )
    print(f"Prueba completada en {round(time.perf_counter() - t0, 2)} s")