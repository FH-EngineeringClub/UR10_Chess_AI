"""
This script controls a UR10 robot to play chess against the Stockfish chess engine.
"""

import platform
import subprocess
import random
import json
import chess
import chess.svg
import chess.engine
from stockfish import Stockfish
from stockfish import StockfishException
from colorama import Fore
import threading
from button_input import connectToButton, listenForButton
import yaml
from robot_api.api import (
    move_to_square,
    disconnect_from_robot,
    direct_move_piece,
    remove_piece,
)

class ChessGame:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.piece_heights = self.config["piece_heights"]
        self.stockfish_difficulty = self.config["stockfish_difficulty_level"]
        self.stockfish_path = self.get_stockfish_path()
        self.zero_player_mode = self.get_zero_player_mode()
        self.board = self.initialize_board()
        self.stockfish = self.initialize_stockfish()
        self.chess_vision_mode = False
        self.chessviz = None
        self.lock = None
        self.setup_vision()

    def load_config(self, config_path):
        with open(config_path, "r") as config_file:
            return yaml.safe_load(config_file)

    def get_stockfish_path(self):
        os_system = platform.system()
        command = "which" if os_system in ("Darwin", "Linux") else "where"
        try:
            result = subprocess.run([command, "stockfish"], capture_output=True, text=True, check=True)
            return result.stdout.strip("\n")
        except subprocess.CalledProcessError:
            raise Exception("No binary or executable found for stockfish")

    def initialize_board(self):
        start_new_game = input(Fore.YELLOW + "Continue last game? (Y/n): ")
        if start_new_game.lower() != "y":
            print(Fore.GREEN + "New game started!")
            return chess.Board()
        try:
            with open("lastgame.txt", "r", encoding="utf-8") as file:
                lastgame = file.read()
                print(Fore.GREEN + "Last game loaded!")
                return chess.Board(lastgame)
        except FileNotFoundError:
            print(Fore.RED + "No last game found, starting new game!")
            return chess.Board()

    def initialize_stockfish(self):
        stockfish = Stockfish(path=self.stockfish_path)
        stockfish.set_depth(8)
        if self.zero_player_mode:
            random_number = random.randint(2000, 3000)
            stockfish.set_elo_rating(random_number)
        else:
            difficulty = input("Enter difficulty (easy, medium, expert, gm): ") or "easy"
            try:
                elo_rating = self.stockfish_difficulty[difficulty]
                stockfish.set_elo_rating(elo_rating)
                print(Fore.GREEN + f"Difficulty set to {difficulty} (ELO {elo_rating})")
            except KeyError:
                print(Fore.RED + "Invalid difficulty level")
                exit()
        return stockfish

    def get_zero_player_mode(self):
        zero_player_mode = input(Fore.LIGHTGREEN_EX + "Zero player mode? (y/N): ")
        return zero_player_mode.lower() == "y"

    def setup_vision(self):
        chess_vision_mode = input(Fore.LIGHTMAGENTA_EX + "Use chess vision? (y/N): ")
        self.chess_vision_mode = chess_vision_mode.lower() == "y"
        if self.chess_vision_mode:
            from vision.chessviz import ChessViz  # Import only when needed
            vision_config = self.config["vision"]
            self.chessviz = ChessViz(
                vision_config["board_corners"][0],
                vision_config["board_corners"][1],
                cam_index=vision_config["cam_index"],
            )
            self.lock = threading.Lock()
            sample_size = self.config["vision"]["sample_size"]
            vision_thread = threading.Thread(
                target=self.chessviz.chess_array_update_thread, args=(sample_size,)
            )
            vision_thread.start()

    def display_board(self):
        with open("chess.svg", "w", encoding="utf-8") as file_obj:
            file_obj.write(chess.svg.board(self.board))

    def save_last_play(self):
        with open("lastgame.txt", "w", encoding="utf-8") as file_obj:
            file_obj.write(self.board.fen())

    def process_move(self, move_str):
        try:
            move = chess.Move.from_uci(move_str)
            if move in self.board.legal_moves:
                self.board.push(move)
                return True
            else:
                print(Fore.RED + "Illegal move.")
                return False
        except ValueError:
            print(Fore.RED + "Invalid move format.")
            return False

    def handle_stockfish_move(self):
        self.stockfish.set_fen_position(self.board.fen())
        best_move = self.stockfish.get_top_moves(1)[0]["Move"]
        uci_format_best_move = chess.Move.from_uci(best_move)
        target_square = uci_format_best_move.to_square
        origin_square = uci_format_best_move.from_square

        move = best_move
        move_pos = Move(self.piece_heights, self.board, data, move)
        if self.board.piece_at(target_square):
            print(Fore.CYAN + f"Space occupied by {self.board.piece_at(target_square)}, removing...")
            move_pos.main_remove_piece()

        move_pos.main_direct_move_piece()
        self.board.push_san(best_move)
        print(Fore.GREEN + f"Stockfish moves: {best_move}")

    def update_board_with_vision(self, chess_array):
        new_fen = self.convert_to_cfen(chess_array)
        for move in self.board.legal_moves:
            self.board.push(move)
            if new_fen == self.board.fen().split(" ")[0]:
                return True
            self.board.pop()
        return False

    def convert_to_cfen(self, chess_array):  # same as before
        rows = []
        for i in range(7, -1, -1):
            row = ""
            empty_count = 0
            for j in range(8):
                piece = chess_array[i][j]
                if piece == ".":
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row += str(empty_count)
                        empty_count = 0
                    row += piece

            if empty_count > 0:
                row += str(empty_count)
            rows.append(row)

        cfen = "/".join(rows)
        return cfen

    def run(self):
        with open("setup.json", encoding="utf-8") as f: # Only open once
            global data # make data available to Move class
            data = json.load(f)
        while not self.board.is_game_over():
            self.display_board()
            self.save_last_play()
            if self.zero_player_mode:
                self.handle_stockfish_move()
            else:
                if self.board.turn == chess.WHITE:
                    print(Fore.WHITE + "White to move")
                    move_to_square()
                    print(Fore.CYAN + "Moving to bin position...")
                    print(Fore.WHITE + "Legal moves:")
                    for move in self.board.legal_moves:
                        move_type = ""
                        if self.board.is_castling(move):
                            move_type = "Castling "
                        elif self.board.is_en_passant(move):
                            move_type = "En Passant "
                        elif self.board.is_capture(move):
                            move_type = "Capture "
                        print(Fore.LIGHTRED_EX + move_type + move.uci(), end=" ")

                    if self.chess_vision_mode:
                        while True:
                            print("\n", "Press enter key to register move.")
                            connectToButton()
                            listenForButton()

                            self.chessviz.counter_on.clear()
                            self.chessviz.counter_on.wait()

                            with self.lock:
                                chess_array = self.chessviz.chess_array
                                print(chess_array)

                            valid_input = self.update_board_with_vision(chess_array)

                            if valid_input:
                                break

                            print("Illegal move, please try again.")
                    else:
                        while True:  # Loop for valid user input
                            inputmove = input(
                                "\n"
                                + Fore.BLUE
                                + "Input move (SAN or UCI, 'undo'):"
                            )

                            if inputmove.lower() == "undo":
                                print("Undoing last move...")
                                try:
                                    for _ in range(2):  # Undo two moves (user and stockfish)
                                        self.board.pop()
                                except IndexError:
                                    print(Fore.RED + "No moves to undo")
                                self.display_board()
                                self.save_last_play()
                                break  # Exit the input loop after undo
                            else:
                                if self.process_move(inputmove):
                                    break # Exit the loop if the move is valid
                    if not self.chess_vision_mode and inputmove.lower() != "undo": # Only ask for confirmation if not vision mode and not undoing
                        user_confirmation = input(Fore.YELLOW + "Confirm move? (y/N): ")
                        if user_confirmation.lower() != "y":
                            self.board.pop() # Undo the move if not confirmed
                            print(Fore.RED + "Move not confirmed.")
                            continue # Go to the next turn
                        
                    if not self.chess_vision_mode or inputmove.lower() != "undo": # Only handle stockfish move if not vision mode or undoing
                        self.handle_stockfish_move()

                else:
                    print(Fore.YELLOW + "Robot is on wrong side, skipping turn")
                    self.board.push_san("0000")  # Push a blank move to the board
                    self.save_last_play()  # Save the last played move

        move_to_square()
        print(Fore.CYAN + "Moving to bin position...")
        print(self.board.outcome())
        print(Fore.GREEN + "Game over!")
        disconnect_from_robot()


class Move:
    def __init__(
        self,
        piece_heights,
        current_board,
        position_data,
        current_move,
    ):
        self.board = current_board
        move_from = current_move[:2]
        move_to = current_move[-2:]
        print(move_from, move_to)
        from_position = position_data[move_from]
        to_position = position_data[move_to]
        from_piece_type = current_board.piece_at(chess.parse_square(move_from))
        to_piece_type = current_board.piece_at(chess.parse_square(move_to))
        print(from_piece_type, to_piece_type)

        if to_piece_type is None:
            to_piece_type = from_piece_type  # Handle cases where no piece is on target square
        to_position_height = piece_heights[to_piece_type.symbol()]
        from_position_height = piece_heights[from_piece_type.symbol()]

        self.from_pos = from_position
        self.to_pos = to_position
        self.from_position_height = from_position_height
        self.to_position_height = to_position_height
        self.to_piece_type = to_piece_type
        self.move_from = move_from
        self.move_to = move_to
        self.is_capture = current_board.is_capture(chess.Move.from_uci(current_move)) # Check if this move is a capture

    def main_direct_move_piece(self):
        """
        Directly move a piece from one position to another on the chess board
        """
        origin_square = chess.parse_square(self.move_from)
        print(
            "Moving piece",
            self.board.piece_at(origin_square),
            "from",
            self.move_from,
            "to",
            self.move_to,
        )
        # Determine REMOVING_PIECE dynamically based on capture
        removing_piece = 1 if self.is_capture else 0 # If it's a capture, we're removing a piece
        direct_move_piece(self, removing_piece)  # Pass removing_piece

    def main_remove_piece(self):
        origin_square = chess.parse_square(self.move_from)
        remove_piece(self, self.board, origin_square)


if __name__ == "__main__":
    game = ChessGame()
    game.run()