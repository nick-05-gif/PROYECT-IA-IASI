import math
import random
import time

try:
    from src.board import Connect4Board
except ImportError:
    from board import Connect4Board


class MCTSNode:
    def __init__(self, board, parent=None, move=None, player_just_moved=None):
        self.board = board
        self.parent = parent
        self.move = move
        self.player_just_moved = player_just_moved
        self.children = []
        self.untried_moves = board.get_valid_moves()
        self.wins = 0.0
        self.visits = 0

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def is_terminal(self):
        return self.board.is_terminal()

    def best_child_ucb(self, c_param):
        # UCB1 balances exploitation (win ratio) and exploration (less visited nodes)
        best_score = -float("inf")
        best_children = []

        for child in self.children:
            exploit = child.wins / child.visits
            explore = c_param * math.sqrt(math.log(self.visits) / child.visits)
            score = exploit + explore

            if score > best_score:
                best_score = score
                best_children = [child]
            elif score == best_score:
                best_children.append(child)

        return random.choice(best_children)

    def expand(self):
        move = self.untried_moves.pop(random.randrange(len(self.untried_moves)))
        next_board = self.board.clone()
        mover = next_board.current_player
        next_board.make_move(move)

        child_node = MCTSNode(
            board=next_board,
            parent=self,
            move=move,
            player_just_moved=mover,
        )
        self.children.append(child_node)
        return child_node


class MCTS:
    def __init__(self, simulations=500, exploration_constant=1.414):
        self.simulations = simulations
        self.exploration_constant = exploration_constant

    def search(self, root_board):
        if root_board.is_terminal():
            return None, {}

        valid_moves = root_board.get_valid_moves()
        if not valid_moves:
            return None, {}

        start_time = time.perf_counter()
        root = MCTSNode(board=root_board.clone())
        nodes_created = 1

        for _ in range(self.simulations):
            node = root

            # 1. Selection
            while not node.is_terminal() and node.is_fully_expanded():
                node = node.best_child_ucb(self.exploration_constant)

            # 2. Expansion
            if not node.is_terminal() and not node.is_fully_expanded():
                node = node.expand()
                nodes_created += 1

            # 3. Simulation (random rollout)
            winner = self._simulate_random_playout(node.board)

            # 4. Backpropagation
            self._backpropagate(node, winner)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Pick the most visited child (robust child criterion)
        best_child = max(root.children, key=lambda c: c.visits)

        column_stats = {}
        for child in root.children:
            win_rate = (child.wins / child.visits) * 100.0 if child.visits > 0 else 0.0
            column_stats[child.move] = {
                "visits": child.visits,
                "wins": child.wins,
                "win_rate": round(win_rate, 1),
            }

        metrics = {
            "best_move": best_child.move,
            "column_stats": column_stats,
            "elapsed_time_ms": round(elapsed_ms, 2),
            "simulations": self.simulations,
            "exploration_constant": self.exploration_constant,
            "nodes_created": nodes_created,
        }

        return best_child.move, metrics

    def _simulate_random_playout(self, board):
        sim_board = board.clone()
        while not sim_board.is_terminal():
            moves = sim_board.get_valid_moves()
            sim_board.make_move(random.choice(moves))
        return sim_board.winner

    def _backpropagate(self, node, winner):
        while node is not None:
            node.visits += 1
            if winner == 0:
                node.wins += 0.5
            elif node.player_just_moved == winner:
                # Track wins from the perspective of the player who made the move into this node
                node.wins += 1.0
            node = node.parent


if __name__ == "__main__":
    board = Connect4Board()
    for col in [0, 6, 1, 6, 2]:
        board.make_move(col)

    print("Board state before AI move:")
    print(board)

    ai = MCTS(simulations=600)
    move, stats = ai.search(board)
    print(f"\nChosen column: {move} (expected 3 to block)")
    print(f"Time: {stats['elapsed_time_ms']} ms | Nodes created: {stats['nodes_created']}")
    for col in sorted(stats["column_stats"]):
        info = stats["column_stats"][col]
        print(f"  Col {col}: {info['visits']} visits | {info['win_rate']}% win rate")