class Connect4Board:
    ROWS = 6
    COLS = 7
    EMPTY = 0
    PLAYER_1 = 1
    PLAYER_2 = 2

    def __init__(self):
        # La fila 0 es la de arriba del todo y la 5 la de abajo (como se dibuja en pantalla)
        self.grid = [[self.EMPTY for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.current_player = self.PLAYER_1
        self.last_move = None
        self.moves_count = 0
        self.winner = None  # None = en juego, 1 o 2 = ganador, 0 = empate
        self.winning_cells = []

    def clone(self):
        # Copia rápida del estado actual para que MCTS simule partidas sin romper la real
        new_board = Connect4Board()
        new_board.grid = [row[:] for row in self.grid]
        new_board.current_player = self.current_player
        new_board.last_move = self.last_move
        new_board.moves_count = self.moves_count
        new_board.winner = self.winner
        new_board.winning_cells = self.winning_cells[:]
        return new_board

    def get_valid_moves(self):
        # Una columna está libre si su casilla superior (fila 0) está vacía
        return [col for col in range(self.COLS) if self.grid[0][col] == self.EMPTY]

    def make_move(self, col):
        if self.winner is not None:
            return False
        if col < 0 or col >= self.COLS or self.grid[0][col] != self.EMPTY:
            return False

        # Buscamos desde abajo hacia arriba dónde cae la ficha por gravedad
        for row in range(self.ROWS - 1, -1, -1):
            if self.grid[row][col] == self.EMPTY:
                self.grid[row][col] = self.current_player
                self.last_move = (row, col)
                self.moves_count += 1

                if self._check_win(row, col, self.current_player):
                    self.winner = self.current_player
                elif self.moves_count == self.ROWS * self.COLS:
                    self.winner = 0  # Tablero lleno sin ganador -> empate
                else:
                    self.current_player = (
                        self.PLAYER_2 if self.current_player == self.PLAYER_1 else self.PLAYER_1
                    )
                return True

        return False

    def _check_win(self, row, col, player):
        # Comprobamos solo las 4 direcciones que pasan por la ficha recién puesta
        directions = [
            (0, 1),   # Horizontal
            (1, 0),   # Vertical
            (1, 1),   # Diagonal principal (\)
            (1, -1),  # Diagonal inversa (/)
        ]

        for dr, dc in directions:
            connected = [(row, col)]

            # Miramos hacia un lado de la dirección
            r, c = row + dr, col + dc
            while 0 <= r < self.ROWS and 0 <= c < self.COLS and self.grid[r][c] == player:
                connected.append((r, c))
                r += dr
                c += dc

            # Miramos hacia el lado contrario
            r, c = row - dr, col - dc
            while 0 <= r < self.ROWS and 0 <= c < self.COLS and self.grid[r][c] == player:
                connected.append((r, c))
                r -= dr
                c -= dc

            if len(connected) >= 4:
                self.winning_cells = connected
                return True

        return False

    def is_terminal(self):
        return self.winner is not None

    def __str__(self):
        symbols = {self.EMPTY: ".", self.PLAYER_1: "X", self.PLAYER_2: "O"}
        lines = [" 0 1 2 3 4 5 6"]
        for row in self.grid:
            lines.append(" " + " ".join(symbols[cell] for cell in row))
        return "\n".join(lines)


if __name__ == "__main__":
    # Prueba rápida en consola para verificar gravedad y detección de victoria
    board = Connect4Board()
    for col in [3, 2, 3, 2, 3, 2, 3]:
        board.make_move(col)
    print(board)
    print(f"Ganador: {board.winner} | Ficha ganadoras: {board.winning_cells}")