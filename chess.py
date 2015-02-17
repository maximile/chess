#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chess! Squares are identified by tuples of ints, 0-7. Y axis is up from white's
point of view:

7 [ ][ ][ ][ ][ ][ ][ ][ ]
6 [ ][ ][ ][ ][ ][ ][ ][ ]  Black's starting side
5 [ ][ ][ ][ ][ ][ ][ ][ ]
4 [ ][ ][ ][ ][ ][ ][ ][ ]
3 [ ][ ][ ][ ][ ][ ][ ][ ]
2 [ ][ ][ ][ ][*][ ][ ][ ]
1 [ ][ ][ ][ ][ ][ ][ ][ ]  White's starting side
0 [ ][ ][ ][ ][ ][ ][ ][ ]
   0  1  2  3  4  5  6  7
   
The squared marked * would be identified by tuple (4, 2). There's no board
class; just a list of pieces each one keeping track of its own position.

"""
import re
import sys
import time
import copy
import random

# Regular expression for a valid grid reference (only used for input)
GRID_REF = re.compile(r"[A-H][1-8]")

# Piece colours
WHITE = True
BLACK = False

# Human-readable colour names
COLOR_NAMES = {WHITE: "white", BLACK: "red"}

# Square colours
DARK = "DARK"
LIGHT = "LIGHT"
HIGHLIGHTED = "HIGHLIGHTED"

# Directions
UP = (0, 1)
UP_RIGHT = (1, 1)
RIGHT = (1, 0)
DOWN_RIGHT = (1, -1)
DOWN = (0, -1)
DOWN_LEFT = (-1, -1)
LEFT = (-1, 0)
UP_LEFT = (-1, 1)

# ANSI color codes
ANSI_BEGIN = "\033[%sm"
ANSI_END = "\033[0m"
ANSI_BG = {DARK: "40", LIGHT: "44", HIGHLIGHTED: "42"}
ANSI_FG = {WHITE: "37", BLACK: "31"}
# ANSI_BG = {DARK: "43", LIGHT: "47"}
# ANSI_FG = {WHITE: "31", BLACK: "30"}

class Piece(object):
    def __init__(self, color, pos):
        if not color in (WHITE, BLACK):
            raise ValueError("Invalid color")
        self.color = color
        self.pos = pos
        self.name = PIECE_NAMES[self.__class__]
        self.value= PIECE_VALUES[self.__class__]
        self.has_moved = False
    
    def __str__(self):
        color_string = COLOR_NAMES[self.color]
        piece_string = PIECE_NAMES[self.__class__]
        pos_string = get_grid_ref_for_pos(self.pos)
        return "%s %s at %s" % (color_string.title(), piece_string, pos_string)
    
    def __repr__(self):
        return self.__str__()
    
    def get_moves_in_direction(self, game, direction):
        """Find all moves along a given direction.
        
        Direction is an offset tuple; e.g. to find all moves to the right
        pass (1, 0).
        
        """
        moves = []
        
        # Start from the current position
        test_move = self.pos
        
        # Keep adding the offset until we hit an invalid move
        while True:
            test_move = (test_move[0] + direction[0],
                         test_move[1] + direction[1])
            
            # Off the board? No more moves in this direction.
            if (test_move[0] < 0 or test_move[0] > 7 or
                test_move[1] < 0 or test_move[1] > 7):
                break
            
            # Hit a piece? Action depends on which color
            hit_piece = game.get_piece_at(test_move)
            if hit_piece:
                if hit_piece.color == self.color:
                    # Same color. It's not a valid move and we can't go
                    # any further.
                    break
                else:
                    # Different color. It's a valid move and we can't go 
                    # any further.
                    moves.append(test_move)
                    break
            
            # Didn't hit anything; it's a valid move.
            moves.append(test_move)
        
        return moves
    
    def remove_invalid_moves(self, game, moves):
        """Given a list of potential moves, remove any that are invalid for
        reasons that apply to all pieces. Reasons:
        
        * Not on the board
        * Taking own piece
        * Doesn't rescue the King from check
        
        """
        valid_moves = []
        for pos in moves:
            # Make sure it's actually a move
            if pos == self.pos:
                continue
            
            # Make sure it's on the board
            if (pos[0] < 0 or pos[0] > 7 or
                pos[1] < 0 or pos[1] > 7):
                # Off the board
                continue
            
            # Make sure it's not taking one of its own pieces
            taken_piece = game.get_piece_at(pos)
            if taken_piece and taken_piece.color == self.color:
                # Taking its own piece
                continue
            
            # TODO: If in check, remove moves that don't rescue the King
            
            valid_moves.append(pos)
        
        return valid_moves    

class Pawn(Piece):
    def get_valid_moves(self, game, testing_check=False):
        moves = []
        
        # Get all the possible squares it can move to
        if self.color == WHITE:
            forward_one = (self.pos[0], self.pos[1] + 1)
            forward_two = (self.pos[0], self.pos[1] + 2)
            take_left = (self.pos[0] - 1, self.pos[1] + 1)
            take_right = (self.pos[0] + 1, self.pos[1] + 1)
        elif self.color == BLACK:
            forward_one = (self.pos[0], self.pos[1] - 1)
            forward_two = (self.pos[0], self.pos[1] - 2)
            take_left = (self.pos[0] + 1, self.pos[1] - 1)
            take_right = (self.pos[0] - 1, self.pos[1] - 1)
        else:
            raise RuntimeError("Never reached.")
        
        # Can move one square forward if the square is vacant
        if not game.get_piece_at(forward_one):
            moves.append(forward_one)
        
        # Can move two squares forward from the starting position
        if ((self.color == WHITE and self.pos[1] == 1) or
            (self.color == BLACK and self.pos[1] == 6)):
            if not game.get_piece_at(forward_two):
                moves.append(forward_two)
        
        # Can take diagonally forward
        for taking_move in take_left, take_right:
            taken_piece = game.get_piece_at(taking_move)
            if taken_piece and not taken_piece.color == self.color:
                moves.append(taking_move)
        
        # En passant
        if game.en_passant_pos in [take_left, take_right]:
            moves.append(game.en_passant_pos)
        
        moves = self.remove_invalid_moves(game, moves)
        
        return moves

class Knight(Piece):
    def get_valid_moves(self, game, testing_check=False):
        moves = []
        
        # [ ][7][ ][0][ ]
        # [6][ ][ ][ ][1]
        # [ ][ ][N][ ][ ]
        # [5][ ][ ][ ][2]
        # [ ][4][ ][3][ ]
        offsets = [(1, 2), (2, 1), (2, -1), (1, -2),
                   (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
        for offset in offsets:
            moves.append((self.pos[0] + offset[0], self.pos[1] + offset[1]))

        # Remove obviously invalid moves
        moves = self.remove_invalid_moves(game, moves)
        return moves
        

class King(Piece):
    def get_valid_moves(self, game, testing_check=False):
        moves = []
        # Clockwise, starting with one square up
        offsets = [UP, UP_RIGHT, RIGHT, DOWN_RIGHT,
                   DOWN, DOWN_LEFT, LEFT, UP_LEFT]
        for offset in offsets:
            moves.append((self.pos[0] + offset[0], self.pos[1] + offset[1]))
        
        # Castling - just handle the King move; the rook move will be done
        # by the game.
        y_pos = self.pos[1]
        queen_rook = game.get_piece_at((0, y_pos))
        king_rook = game.get_piece_at((7, y_pos))
        for rook in queen_rook, king_rook:
            # Don't worry about castling when testing check.
            if testing_check:
                continue
            
            if not rook:
                continue
            
            # Can't castle out of check
            if game.in_check(self.color):
                continue
            
            # Neither the rook nor the king can have moved
            if self.has_moved or rook.has_moved:
                continue
            
            # Squares between the king and rook must be vacant
            squares_between = []
            if rook.pos[0] < self.pos[0]:  # Queen side
                squares_between = [(1, y_pos), (2, y_pos), (3, y_pos)]
            else:  # King side
                squares_between = [(5, y_pos), (6, y_pos)]
            all_squares_vacant = True
            for square in squares_between:
                if game.get_piece_at(square):
                    all_squares_vacant = False
            if not all_squares_vacant:
                continue
            
            # None of the squares in between can put the King in check
            crosses_check = False
            for square in squares_between:
                test_game = copy.deepcopy(game)
                test_game.move_piece_to(self, square)
                if test_game.in_check(self.color):
                    crosses_check = True
                    break
            if crosses_check:
                continue
            
            # Castling on this side is allowed
            if rook == queen_rook:
                moves.append((2, self.pos[1]))
            else:
                moves.append((6, self.pos[1]))
        
        # Remove obviously invalid moves
        moves = self.remove_invalid_moves(game, moves)
        return moves


class Queen(Piece):
    def get_valid_moves(self, game, testing_check=False):
        moves = []
        
        # All directions are valid
        directions = [UP, UP_RIGHT, RIGHT, DOWN_RIGHT,
                      DOWN, DOWN_LEFT, LEFT, UP_LEFT]
        
        # Keep moving in each direction until we hit a piece or the edge 
        # of the board.
        for direction in directions:
            moves.extend(self.get_moves_in_direction(game, direction))
        
        moves = self.remove_invalid_moves(game, moves)    
        return moves


class Bishop(Piece):
    def get_valid_moves(self, game, testing_check=False):
        moves = []
        
        # Diagonals only
        directions = [UP_LEFT, UP_RIGHT, DOWN_LEFT, DOWN_RIGHT]
        
        # Keep moving in each direction until we hit a piece or the edge 
        # of the board.
        for direction in directions:
            moves.extend(self.get_moves_in_direction(game, direction))

        moves = self.remove_invalid_moves(game, moves)
        return moves


class Rook(Piece):
    def get_valid_moves(self, game, testing_check=False):
        moves = []
        
        # Horizontal and vertical only
        directions = [UP, RIGHT, LEFT, DOWN]
        
        # Keep moving in each direction until we hit a piece or the edge 
        # of the board.
        for direction in directions:
            moves.extend(self.get_moves_in_direction(game, direction))

        moves = self.remove_invalid_moves(game, moves)
        return moves


# Characters to represent pieces
SELECTED_PIECE_CHARACTERS = {King: "♚",
                             Queen: "♛",
                             Rook: "♜",
                             Bishop: "♝",
                             Knight: "♞",
                             Pawn: "♟"}
PIECE_CHARACTERS = {King: "♔",
                    Queen: "♕",
                    Rook: "♖",
                    Bishop: "♗",
                    Knight: "♘",
                    Pawn: "♙"}

# Human readable piece names
PIECE_NAMES = {King: "king",
               Queen: "queen",
               Rook: "rook",
               Bishop: "bishop",
               Knight: "knight",
               Pawn: "pawn"}

# Values for AI
PIECE_VALUES = {King: 9999,
                Queen: 9,
                Rook: 5,
                Bishop: 3,
                Knight: 3,
                Pawn: 1}


class EndGame(Exception):
    pass

class Game(object):
    def __init__(self):
        """Set up initial state.
        
        """
        # List of all pieces in the game
        self._pieces = []
        
        # General state
        self.color_to_move = WHITE
        # Number of moves without a pawn move or a take
        self.idle_move_count = 0
        
        # Setup initial position. First, setup pawns:
        for x in range(8):
            self._pieces.append(Pawn(WHITE, (x,1)))
            self._pieces.append(Pawn(BLACK, (x,6)))
        
        # Various state
        self.last_moved_piece = None
        self.en_passant_pos = None
        
        # Other pieces
        officer_ranks = {WHITE: 0, BLACK: 7}
        for color, rank in officer_ranks.items():
            self._pieces.append(Rook(color, (0, rank)))
            self._pieces.append(Knight(color, (1, rank)))
            self._pieces.append(Bishop(color, (2, rank)))
            self._pieces.append(Queen(color, (3, rank)))
            self._pieces.append(King(color, (4, rank)))
            self._pieces.append(Bishop(color, (5, rank)))
            self._pieces.append(Knight(color, (6, rank)))
            self._pieces.append(Rook(color, (7, rank)))
    
    def get_piece_at(self, pos):
        """The piece at the given position.
        
        """
        for piece in self._pieces:
            if piece.pos == pos:
                return piece
    
    def move_piece_to(self, piece, pos):
        """Update the piece's position, removing any existing piece.
                
        """
        # Don't need to worry about accidentally moving pieces from other games
        piece = self.get_piece_at(piece.pos)
                
        previous_piece = self.get_piece_at(pos)
        
        # Check for taking
        if previous_piece:
            # Make sure it's a different colour (should be caught elsewhere)
            if previous_piece.color == piece.color:
                raise RuntimeError("%s tried to take own %s." %
                                   (piece.name.title(), previous_piece.name))
            # Make sure it's not a king
            if previous_piece.__class__ == King:
                raise RuntimeError("%s took %s!" % (piece, previous_piece))
            
            # Remove the piece
            self._pieces.remove(previous_piece)
        
        # Move the piece
        old_pos = piece.pos
        piece.pos = pos

        # Handle special cases. Pawns:
        if piece.__class__ == Pawn:
            # Promotion. TODO: Handle promotion to other officers
            if (piece.color == WHITE and piece.pos[1] == 7 or
                piece.color == BLACK and piece.pos[1] == 0):
                self._pieces.remove(piece)
                self._pieces.append(Queen(piece.color, piece.pos))

            # En passant
            if piece.pos == self.en_passant_pos:
                if piece.pos[1] == 2:
                    taken_pawn = self.get_piece_at((piece.pos[0], 3))
                elif piece.pos[1] == 5:
                    taken_pawn = self.get_piece_at((piece.pos[0], 4))
                else:
                    raise RuntimeError("Messed up en passant.")
                if not taken_pawn:
                    raise RuntimeError("Messed up en passant again.")
                self._pieces.remove(taken_pawn)
        
        # Castling
        if piece.__class__ == King:
            if old_pos[0] - pos[0] == 2:  # Queen side castling
                queen_rook = self.get_piece_at((0, pos[1]))
                queen_rook.pos = (3, pos[1])
                queen_rook.has_moved = True
            if old_pos[0] - pos[0] == -2:  # King side castling
                king_rook = self.get_piece_at((7, pos[1]))
                king_rook.pos = (5, pos[1])
                king_rook.has_moved = True
        
        # Update en passant status
        if (piece.__class__ == Pawn and piece.pos[1] in [3,4] and
            not piece.has_moved):
            if piece.pos[1] == 3:
                self.en_passant_pos = ((piece.pos[0], 2))
            else:
                self.en_passant_pos = ((piece.pos[0], 5))
        else:
            self.en_passant_pos = None
        
        # Update game state for castling etc.
        piece.has_moved = True
        self.last_moved_piece = piece
                
        # Alter idle move count - reset if it's a take or a pawn move
        if piece.__class__ == Pawn or previous_piece:
            self.idle_move_count = 0
        else:
            self.idle_move_count += 1
        
    def check_endgame(self):
        """Raises EndGame if the previous move ended the game.
        
        """
        # See if that's the end of the game
        if not self.get_valid_moves(self.color_to_move):
            # In check? That's checkmate
            if self.in_check():
                raise EndGame("Checkmate! %s wins" %
                              COLOR_NAMES[not self.color_to_move].title())
            else:
                raise EndGame("Stalemate!")
        
        if self.idle_move_count >= 50:
            raise EndGame("Draw (fifty idle moves)")
    
    def is_piece_at_risk(self, piece):
        """If the piece can be taken.
        
        """
        their_moves = self.get_valid_moves(not piece.color, testing_check=True)
        for move in their_moves:
            if self.get_piece_at(move[1]) == piece:
                # They have a move that could potentially take the piece
                # on the next turn
                return True
        return False
                
    def in_check(self, color=None):
        """If the current player's King is under threat.
        
        """
        if color is None:
            color = self.color_to_move
        
        # See if any of the other player's moves could take the king
        our_king = [piece for piece in self._pieces if
                    piece.__class__ == King and piece.color == color][0]
        if self.is_piece_at_risk(our_king):
            return True
        
        # The king isn't under attack
        return False
    
    def get_pieces(self, color=None):
        """Pieces with the given color, or all pieces.
        
        """
        if color is None:
            return self._pieces
        return [piece for piece in self._pieces if piece.color == color]
    
    def get_valid_moves_for_piece(self, piece, testing_check=False):
        """Get the moves the given piece can legally make.
        
        """
        moves = []
        
        # Get every possible move
        for pos in piece.get_valid_moves(self, testing_check=testing_check):
            moves.append((piece, pos))
        
        # If we're not worried about putting ourself in check, we're done.
        if testing_check:
            return moves
        
        # Filter out moves that would put the King in check
        would_check = []
        for move in moves:
            test_game = copy.deepcopy(self)
            test_game.move_piece_to(move[0], move[1])
            if test_game.in_check(piece.color):
                would_check.append(move)
        
        return [move for move in moves if not move in would_check]
    
    def get_valid_moves(self, color, testing_check=False):
        """All possible moves for the given color.
        
        Returns a list of tuples, piece then move. Includes taking the King,
        so check should be handled separately. Pass testing_check to allow moves
        that would put the King at risk.
        
        """
        moves = []
        
        # Get every possible move
        for piece in self.get_pieces(color):
            moves.extend(self.get_valid_moves_for_piece(piece,
                                                testing_check=testing_check))
        return moves

def get_coords_for_grid_ref(grid_ref):
    """Convert traditional coordinates to our coordinates.

    e.g. A1 -> (0, 0)
         H8 -> (7, 7)

    """
    x_for_file = {"A": 0,"B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6,
                  "H": 7}
    y_for_rank = {"1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6,
                  "8": 7}
    file_letter = grid_ref[0]
    rank_number = grid_ref[1]
    return (x_for_file[file_letter], y_for_rank[rank_number])

def get_grid_ref_for_pos(coords):
    """Convert traditional coordinates to our coordinates.

    e.g. A1 -> (0, 0)
         H8 -> (7, 7)

    """
    files = ["A", "B", "C", "D", "E", "F", "G", "H"]
    ranks = ["1", "2", "3", "4", "5", "6", "7", "8"]
    return (files[coords[0]] + ranks[coords[1]])

def draw_game(game, selected_piece=None):
    # Get a string for each rank
    rank_strings = []
    
    # Get possible moves for selected piece
    if selected_piece:
        valid_moves = game.get_valid_moves_for_piece(selected_piece)
        valid_squares = [move[1] for move in valid_moves]
    else:
        valid_squares = []
    
    # Ranks, top to bottom:
    for y in reversed(range(8)):
        rank_string = " %i " % (y + 1)
        for x in range(8):
            # Get foreground text (must make up two characters)
            piece = game.get_piece_at((x, y))
            if piece:
                if piece == selected_piece or piece == game.last_moved_piece:
                    piece_char = SELECTED_PIECE_CHARACTERS[piece.__class__]
                else:
                    piece_char = PIECE_CHARACTERS[piece.__class__]
                foreground_text = piece_char + " "
            else:
                foreground_text = "  "
            
            # Get background colour
            if (x, y) in valid_squares:
                square_color = HIGHLIGHTED
            elif x % 2 == y % 2:
                square_color = DARK
            else:
                square_color = LIGHT
            piece_color = WHITE
            if piece and piece.color == BLACK:
                piece_color = BLACK
            begin_code = ANSI_BEGIN % "%s;%s" % (ANSI_BG[square_color],
                                                 ANSI_FG[piece_color])
            rank_string += "%s%s%s" % (begin_code, foreground_text, ANSI_END)
        rank_strings.append(rank_string)
    file_labels = "   A B C D E F G H"
    
    print "\n".join(rank_strings) + "\n" + file_labels


def main():
    game = Game()
    
    # Get the game type
    print "Let's play chess! Select a game type:"
    print
    print "1. Computer vs. computer"
    print "2. Computer vs. human"
    print "3. Human vs. computer"
    print "4. Human vs. human"
    print
    while True:
        option = raw_input("Selection: ").strip()
        if not option in ["1", "2", "3", "4"]:
            print "Select an option above (1-4)"
            continue
        if option == "1":
            players = {WHITE: ComputerPlayer(game, WHITE),
                       BLACK: ComputerPlayer(game, BLACK)}
        elif option == "2":
            players = {WHITE: ComputerPlayer(game, WHITE),
                       BLACK: HumanPlayer(game, BLACK)}
        elif option == "3":
            players = {WHITE: HumanPlayer(game, WHITE),
                       BLACK: ComputerPlayer(game, BLACK)}
        elif option == "4":
            players = {WHITE: HumanPlayer(game, WHITE),
                       BLACK: HumanPlayer(game, BLACK)}
        else:
            raise RuntimeError("Never reached.")
        break
    
    # Main game loop
    try:
        while True:
            # time.sleep(0.01)
            draw_game(game)
            
            player_to_move = players[game.color_to_move]
            move = player_to_move.get_move()
            game.move_piece_to(move[0], move[1])
            game.color_to_move = not game.color_to_move
            game.check_endgame()
            
    except EndGame as e:
        draw_game(game)
        print e
    

class Player(object):
    def __init__(self, game, color):
        self.game = game
        self.color = color
    
class ComputerPlayer(Player):
    def get_move(self):
        if not self.game.color_to_move == self.color:
            raise RuntimeError("Not my turn!")
        
        available_moves = self.game.get_valid_moves(self.color)
        
        # Find checking moves
        checking_moves = []
        riskless_checking_moves = []
        for move in available_moves:
            test_game = copy.deepcopy(self.game)
            test_game.move_piece_to(move[0], move[1])
            if test_game.in_check(not self.color):
                # Check for potential mates
                if not test_game.get_valid_moves(not self.color):
                    return move
                checking_moves.append(move)
                if not test_game.is_piece_at_risk(move[0]):
                    riskless_checking_moves.append(move)
        
        # Find taking moves
        taking_moves = [move for move in available_moves if
                        self.game.get_piece_at(move[1])]
        
        # Retreats
        retreats = {}
        for move in available_moves:
            if self.game.is_piece_at_risk(move[0]):
                test_game = copy.deepcopy(self.game)
                test_game.move_piece_to(move[0], move[1])
                if test_game.is_piece_at_risk(test_game.get_piece_at(move[1])):
                    continue
                retreats[move] = move[0].value
        highest_value = -999999
        best_retreat = None
        for move, value in retreats.items():
            if value > highest_value:
                best_retreat = move
                highest_value = value
        if best_retreat:
            return best_retreat
        
        # Find riskless taking moves (free material)
        riskless_taking_moves = []
        for move in taking_moves:
            test_game = copy.deepcopy(self.game)
            test_game.move_piece_to(move[0], move[1])
            if not test_game.is_piece_at_risk(test_game.get_piece_at(move[1])):
                riskless_taking_moves.append(move)
        if riskless_taking_moves:
            return random.choice(riskless_taking_moves)
        
        # A check is pretty good if it doesn't cost anything
        if riskless_checking_moves:
            return random.choice(riskless_checking_moves)
        
        # Find the best value taking move
        valued_taking_moves = {}
        for move in taking_moves:
            our_piece = move[0]
            their_piece = self.game.get_piece_at(move[1])
            move_value = their_piece.value - our_piece.value
            valued_taking_moves[move] = move_value
        highest_value = -999999
        best_taking_move = None
        for move, value in valued_taking_moves.items():
            if value > highest_value:
                best_taking_move = move
                highest_value = value
        
        # Find pawn moves
        pawn_moves = [move for move in available_moves if
                      move[0].__class__ == Pawn]
        
        # Good options
        good_options = []
        if pawn_moves:
            good_options.append(random.choice(pawn_moves))
        if checking_moves:
            good_options.append(checking_moves)
        if best_taking_move:
            good_options.append(best_taking_move)
        if good_options:
            return random.choice(good_options)
        
        # Make any move
        return random.choice(available_moves)

class HumanPlayer(Player):
    def get_move(self):
        """Get command line input to move the piece.
        
        """
        # Loop until we have a valid move
        while True:
            # Print status
            if self.game.in_check(self.color):
                check_string = " (You're in check!)"
            else:
                check_string = ""
            print "%s to play.%s" % (COLOR_NAMES[self.color].title(),
                                     check_string)
            
            # Get user input
            move_string = raw_input("Your move: ").strip().upper()
            
            # Is it an explicit move (from -> to)?
            explicit_match = re.match(r"([A-H][1-8]).*([A-H][1-8])",
                                      move_string)
            if explicit_match:
                from_ref = explicit_match.group(1)
                to_ref = explicit_match.group(2)
                from_pos = get_coords_for_grid_ref(from_ref)
                to_pos = get_coords_for_grid_ref(to_ref)
                piece = self.game.get_piece_at(from_pos)
                
                # Validate the move
                if not piece:
                    print "No piece at %s" % from_ref
                    continue
                if not piece.color == self.color:
                    print "That's not your %s!" % piece.name
                    continue
                valid_moves = self.game.get_valid_moves_for_piece(piece)
                valid_squares = [move[1] for move in valid_moves]
                if not to_pos in valid_squares:
                    print "That %s can't move to %s!" % (piece.name, to_ref)
                    continue
                return (piece, to_pos)
            
            # Specified a single square
            if not re.match(r"[A-H][1-8]", move_string):
                print "That's not a valid move. Examples: 'A8', 'D2D4', etc."
                continue
            pos = get_coords_for_grid_ref(move_string)
            piece_on_target = self.game.get_piece_at(pos)
            
            # If it's not one of ours, see if any of our pieces can move there
            if not piece_on_target or not piece_on_target.color == self.color:
                valid_moves = self.game.get_valid_moves(self.color)
                moves_to_target = [move for move in valid_moves if
                                   move[1] == pos]
                if not moves_to_target:
                    action_string = "move there"
                    if piece_on_target:
                        action_string = ("take that %s" %
                                         PIECE_NAMES[piece_on_target.__class__])
                    print "None of your pieces can %s." % action_string
                    continue
                elif len(moves_to_target) == 2:
                    piece_one = moves_to_target[0][0]
                    piece_two = moves_to_target[1][0]
                    if piece_one.__class__ == piece_two.__class__:
                        print "Two %ss can move there." % piece_one.name
                    else:
                        print ("The %s and the %s can both move there." %
                               (piece_one.name, piece_two.name))
                    continue
                elif len(moves_to_target) > 1:
                    print "Lots of pieces can move there."
                    continue
                elif len(moves_to_target) == 1:
                    return moves_to_target[0]
                else:
                    raise RuntimeError("Never reached.")
            
            # It's one of ours; show where it can move and ask again
            piece = piece_on_target
            valid_moves = self.game.get_valid_moves_for_piece(piece)
            if not valid_moves:
                print "That %s has nowhere to go!" % piece.name
                continue
            
            # Move the piece
            draw_game(self.game, selected_piece=piece)
            input_string = raw_input("Move the %s to: " % piece.name).strip().upper()
            if not GRID_REF.match(input_string):
                draw_game(self.game)
                print "That's not a square!"
                continue
            coords = get_coords_for_grid_ref(input_string)
            valid_squares = [move[1] for move in valid_moves]
            if coords == piece.pos:
                draw_game(self.game)
                print "That %s is already on %s!" % (piece.name, input_string)
                continue
            if not coords in valid_squares:
                draw_game(self.game)
                print "That %s can't move to %s" % (piece.name, input_string)
                continue
            return (piece, coords)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "\nBye!"
        sys.exit()