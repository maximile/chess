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
import time
import copy
import random

# Regular expression for a valid grid reference (only used for input)
GRID_REF = re.compile(r"[A-H][1-8]")

# Piece colours
WHITE = True
BLACK = False

# Human-readable colour names
COLOR_NAMES = {WHITE: "white", BLACK: "black"}

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
    def get_valid_moves(self, game):
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
        
        # TODO: en passant
        
        moves = self.remove_invalid_moves(game, moves)
        
        return moves

class Knight(Piece):
    def get_valid_moves(self, game):
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
    def get_valid_moves(self, game):
        moves = []
        # Clockwise, starting with one square up
        offsets = [UP, UP_RIGHT, RIGHT, DOWN_RIGHT,
                   DOWN, DOWN_LEFT, LEFT, UP_LEFT]
        for offset in offsets:
            moves.append((self.pos[0] + offset[0], self.pos[1] + offset[1]))
        
        # TODO: Castling
        
        # Remove obviously invalid moves
        moves = self.remove_invalid_moves(game, moves)
        return moves


class Queen(Piece):
    def get_valid_moves(self, game):
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
    def get_valid_moves(self, game):
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
    def get_valid_moves(self, game):
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
PIECE_CHARACTERS = {King: "♚",
                    Queen: "♛",
                    Rook: "♜",
                    Bishop: "♝",
                    Knight: "♞",
                    Pawn: "♟"}
SELECTED_PIECE_CHARACTERS = {King: "♔",
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
        
        # Make sure nothing weird is happening
        if not piece.color == self.color_to_move:
            raise RuntimeError("Not that piece's turn.")
        
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
        piece.pos = pos
        
        # Handle special cases. Promotion:
        if piece.__class__ == Pawn:
            # TODO: Handle promotion to other officers
            if (piece.color == WHITE and piece.pos[1] == 7 or
                piece.color == BLACK and piece.pos[1] == 0):
                self._pieces.remove(piece)
                self._pieces.append(Queen(piece.color, piece.pos))
        # TODO: en passant, castling
        
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
    
    def in_check(self, color=None):
        """If the current player's King is under threat.
        
        """
        if not color:
            color = self.color_to_move
        
        # All the moves the opposing player could make
        their_color = not color
        
        # See if any of the other player's moves could take the king
        our_king = [piece for piece in self._pieces if
                    piece.__class__ == King and piece.color == color][0]
        their_moves = self.get_valid_moves(their_color, ignore_check=True)
        for move in their_moves:
            if self.get_piece_at(move[1]) == our_king:
                # They have a move that could potentially take the King
                # on the next turn
                return True
        
        # The king isn't under attack
        return False
    
    def get_pieces(self, color=None):
        """Pieces with the given color, or all pieces.
        
        """
        if color is None:
            return self._pieces
        return [piece for piece in self._pieces if piece.color == color]
    
    def get_valid_moves(self, color, ignore_check=False):
        """All possible moves for the given color.
        
        Returns a list of tuples, piece then move. Includes taking the King,
        so check should be handled separately. Pass ignore_check to allow moves
        that would put the King at risk.
        
        """
        moves = []
        
        # Get every possible move
        for piece in self.get_pieces(color):
            for pos in piece.get_valid_moves(self):
                moves.append((piece, pos))
        
        # If we're not worried about putting ourself in check, we're done.
        if ignore_check:
            return moves
        
        # Filter out moves that would put the King in check
        would_check = []
        for move in moves:
            test_game = copy.deepcopy(self)
            test_game.move_piece_to(piece, move[1])
            if test_game.in_check(color):
                would_check.append(move)
            # # Move the piece, test for check, then move it back
            # piece, pos = move
            # old_pos = piece.pos
            # old_piece = self.get_piece_at(pos)
            # if old_piece:
            #     self._pieces.remove(old_piece)
            # piece.pos = pos
            # if self.in_check(color):
            #     would_check.append(move)
            # # Put them back
            # piece.pos = old_pos
            # if old_piece:
            #     self._pieces.append(old_piece)
        
        return [move for move in moves if not move in would_check]

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
        valid_moves = selected_piece.get_valid_moves(game)
    else:
        valid_moves = []
    
    # Ranks, top to bottom:
    for y in reversed(range(8)):
        rank_string = " %i " % (y + 1)
        for x in range(8):
            # Get foreground text (must make up two characters)
            piece = game.get_piece_at((x, y))
            if piece:
                if piece == selected_piece:
                    piece_char = SELECTED_PIECE_CHARACTERS[piece.__class__]
                else:
                    piece_char = PIECE_CHARACTERS[piece.__class__]
                foreground_text = piece_char + " "
            else:
                foreground_text = "  "
            
            # Get background colour
            if (x, y) in valid_moves:
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
    
    players = {BLACK: ComputerPlayer(game, BLACK),
               WHITE: ComputerPlayer(game, WHITE)}
    
    try:
        while True:
            # time.sleep(0.01)
            draw_game(game)
            
            player_to_move = players[game.color_to_move]
            move = player_to_move.get_move()
            game.move_piece_to(move[0], move[1])
            game.color_to_move = not game.color_to_move
            game.check_endgame()
            
    except EndGame:
        draw_game(game)
        raise
    

class Player(object):
    def __init__(self, game, color):
        self.game = game
        self.color = color
    
class ComputerPlayer(Player):
    def get_move(self):
        if not self.game.color_to_move == self.color:
            raise RuntimeError("Not my turn!")
        
        available_moves = self.game.get_valid_moves(self.color)
        taking_moves = [move for move in available_moves if
                        self.game.get_piece_at(move[1])]
        
        # Find checking moves
        checking_moves = []
        for move in available_moves:
            test_game = copy.deepcopy(game)
            test_game.move_piece_to(move[0], move[1])
            if test_game.in_check(not self.color):
                checking_moves.append(move)
        
        if checking_moves:
            best_move = random.choice(checking_moves)
        elif taking_moves:
            best_move = random.choice(taking_moves)
        else:
            best_move = random.choice(available_moves)
        
        return best_move

class HumanPlayer(Player):
    def get_move(self):
        """Get command line input to move the piece.
        
        """
        while True:
            # Select a piece
            piece = None
            input_string = raw_input("Move piece at: ").strip().upper()
            if not GRID_REF.match(input_string):
                print "That's not a square (e.g. A1)"
                continue
            coords = get_coords_for_grid_ref(input_string)
            piece = self.game.get_piece_at(coords)
            if not piece:
                print "No piece at %s" % input_string
                continue
            if not piece.color == self.color:
                print "That's not your %s!" % piece.name
                continue
            if not piece.get_valid_moves(self.game):
                print "That %s has nowhere to go!" % piece.name
                continue
            
            # Move the piece
            draw_game(self.game, selected_piece=piece)
            input_string = raw_input("Move the %s to: " % piece.name).strip().upper()
            if not GRID_REF.match(input_string):
                print "That's not a square!"
                continue
            coords = get_coords_for_grid_ref(input_string)
            if not coords in piece.get_valid_moves(self.game):
                print "That %s can't move to %s" % (piece.name, input_string)
                continue
            move = (piece, coords)
            break
        return move

if __name__ == "__main__":
    main()