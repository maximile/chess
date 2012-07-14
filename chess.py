#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

# Piece colours
WHITE = "WHITE"
BLACK = "BLACK"

# Square colours
DARK = "DARK"
LIGHT = "LIGHT"

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
ANSI_BG = {DARK: "40", LIGHT: "44"}
ANSI_FG = {WHITE: "37", BLACK: "31"}
# ANSI_BG = {DARK: "43", LIGHT: "47"}
# ANSI_FG = {WHITE: "31", BLACK: "30"}


class Piece(object):
    def __init__(self, color):
        if not color in (WHITE, BLACK):
            raise ValueError("Invalid color")
        self.color = color
        self.pos = None
        self.name = PIECE_NAMES[self.__class__]
        
    def get_moves_in_direction(self, direction):
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
            hit_piece = self.board.get_piece_at(test_move)
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
    
    def remove_invalid_moves(self, moves):
        """Given a list of potential moves, remove any that are invalid for
        reasons that apply to all pieces. Reasons:
        
        * Not on the board
        * Taking own piece
        * Doesn't rescue the King from check
        
        """
        valid_moves = []
        for move in moves:
            # Make sure it's actually a move
            if self.move == self.pos:
                continue
            
            # Make sure it's on the board
            if (self.move[0] < 0 or self.move[0] > 7 or
                self.move[1] < 0 or self.move[1] > 7):
                # Off the board
                continue
            
            # Make sure it's not taking one of its own pieces
            taken_piece = self.board.get_piece_at(move)
            if taken_piece and taken_piece.color == self.color:
                # Taking its own piece
                continue
            
            # TODO: If in check, remove moves that don't rescue the King
            
            valid_moves.append(move)
        
        return valid_moves    

class Pawn(Piece):
    def get_valid_moves(self):
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
        
        # Always able to move one square forward
        moves.append(forward_one)
        
        # Can move two squares forward from the starting position
        if ((self.color == WHITE and self.pos[1] == 1) or
            (self.color == BLACK and self.pos[1] == 6)):
            moves.append(forward_two)
        
        # Can take diagonally forward
        for taking_move in take_left, take_right:
            taken_piece = self.board.get_piece_at(taking_move)
            if taken_piece and not taken_piece.color == self.color:
                moves.append(taking_move)
        
        # TODO: en passant
        
        return moves

class Knight(Piece):
    def get_valid_moves(self):
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
        moves = self.remove_invalid_moves(moves)
        

class King(Piece):
    def get_valid_moves(self):
        moves = []
        # Clockwise, starting with one square up
        offsets = [UP, UP_RIGHT, RIGHT, DOWN_RIGHT,
                   DOWN, DOWN_LEFT, LEFT, UP_LEFT]
        for offset in offsets:
            moves.append((self.pos[0] + offset[0], self.pos[1] + offset[1]))
        
        # Remove obviously invalid moves
        moves = self.remove_invalid_moves(moves)
        
        # TODO: Remove moves that would put the king in check
        
        # TODO: Castling
        
        return moves


class Queen(Piece):
    def get_valid_moves(self):
        moves = []
        
        # All directions are valid
        directions = [UP, UP_RIGHT, RIGHT, DOWN_RIGHT,
                      DOWN, DOWN_LEFT, LEFT, UP_LEFT]
        
        # Keep moving in each direction until we hit a piece or the edge 
        # of the board.
        for direction in directions:
            moves.extend(self.get_moves_in_direction(direction))
        
        return moves


class Bishop(Piece):
    def get_valid_moves(self):
        moves = []
        
        # Diagonals only
        directions = [UP_LEFT, UP_RIGHT, DOWN_LEFT, DOWN_RIGHT]
        
        # Keep moving in each direction until we hit a piece or the edge 
        # of the board.
        for direction in directions:
            moves.extend(self.get_moves_in_direction(direction))

        return moves


class Rook(Piece):
    def get_valid_moves(self):
        moves = []
        
        # Horizontal and vertical only
        directions = [UP, RIGHT, LEFT, DOWN]
        
        # Keep moving in each direction until we hit a piece or the edge 
        # of the board.
        for direction in directions:
            moves.extend(self.get_moves_in_direction(direction))

        return moves


# Characters to represent pieces
PIECE_CHARACTERS = {King: "♚",
                    Queen: "♛",
                    Rook: "♜",
                    Bishop: "♝",
                    Knight: "♞",
                    Pawn: "♟"}

# Human readable piece names
PIECE_NAMES = {King: "king",
               Queen: "queen",
               Rook: "rook",
               Bishop: "bishop",
               Knight: "knight",
               Pawn: "pawn"}


class Board(object):
    """Array of squares, each of which can hold one piece.
    
    Y axis is up from white's point of view:
    
    7 [ ][ ][ ][ ][ ][ ][ ][ ]
    6 [ ][ ][ ][ ][ ][ ][ ][ ]  Black's starting side
    5 [ ][ ][ ][ ][ ][ ][ ][ ]
    4 [ ][ ][ ][ ][ ][ ][ ][ ]
    3 [ ][ ][ ][ ][ ][ ][ ][ ]
    2 [ ][ ][ ][ ][*][ ][ ][ ]
    1 [ ][ ][ ][ ][ ][ ][ ][ ]  White's starting side
    0 [ ][ ][ ][ ][ ][ ][ ][ ]
       0  1  2  3  4  5  6  7
       
    The squared marked * would be addressed by tuple (4, 2)
    
    """
    def __init__(self, default_starting_position=True):
        # Pieces stored in a list of lists. None if no piece.
        self._pieces = []
        for rank in range(8):
            squares = []
            for file in range(8):
                squares.append(None)
            self._pieces.append(squares)
        
        if default_starting_position:
            # Setup pawns
            for x in range(8):
                self.move_piece_to(Pawn(WHITE), (x, 1))
                self.move_piece_to(Pawn(BLACK), (x, 6))
            
            # Other pieces
            officer_ranks = {WHITE: 0, BLACK: 7}
            for color, rank in officer_ranks.items():
                self.move_piece_to(Rook(color), (0, rank))
                self.move_piece_to(Knight(color), (1, rank))
                self.move_piece_to(Bishop(color), (2, rank))
                self.move_piece_to(Queen(color), (3, rank))
                self.move_piece_to(King(color), (4, rank))
                self.move_piece_to(Bishop(color), (5, rank))
                self.move_piece_to(Knight(color), (6, rank))
                self.move_piece_to(Rook(color), (7, rank))
    
    def move_piece_to(self, piece, pos):
        if not piece.pos is None:
            self._pieces[piece.pos[0]][piece.pos[1]] = None
        self._pieces[pos[0]][pos[1]] = piece
        piece.pos = pos
        piece.board = self

    def get_piece_at(self, pos):
        return self._pieces[pos[0]][pos[1]]
    
    def get_string_rep(self, color=True, selected_piece=None):
        """String representation of the board and pieces.
        
        """
        # Get a string for each rank
        rank_strings = []
        
        # Ranks, top to bottom:
        for y in reversed(range(8)):
            rank_string = " %i " % (y + 1)
            for x in range(8):
                piece = self.get_piece_at((x, y))
                if piece:
                    piece_char = PIECE_CHARACTERS[piece.__class__]
                else:
                    piece_char = " "
                if color:
                    if x % 2 == y % 2:
                        square_color = DARK
                    else:
                        square_color = LIGHT
                    piece_color = WHITE
                    if piece and piece.color == BLACK:
                        piece_color = BLACK
                    begin_code = ANSI_BEGIN % "%s;%s" % (ANSI_BG[square_color],
                                                         ANSI_FG[piece_color])
                    rank_string += "%s%s %s" % (begin_code, piece_char, ANSI_END)
                else:
                    rank_string += "[%s " % piece_char
            rank_strings.append(rank_string)
        file_labels = "   A B C D E F G H"
        return "\n".join(rank_strings) + "\n" + file_labels
        
    def get_coords_for_grid_ref(self, file_letter, rank_number):
        """Convert traditional coordinates to our coordinates.
        
        e.g. A1 -> (0, 0)
             H8 -> (7, 7)
        
        """
        x_for_file = {"A": 0,
                      "B": 1,
                      "C": 2,
                      "D": 3,
                      "E": 4,
                      "F": 5,
                      "G": 6,
                      "H": 7}
        y_for_rank = {"1": 0,
                      "2": 1,
                      "3": 2,
                      "4": 3,
                      "5": 4,
                      "6": 5,
                      "7": 6,
                      "8": 7}
        return (x_for_file[file_letter], y_for_rank[rank_number])
    
    def __str__(self):
        return self.get_string_rep(color=False)

def main():
    board = Board()
    
    # Main loop
    while True:
        # Draw the board
        print board.get_string_rep()
        
        # Select a piece
        piece = None
        selection_string = raw_input("Move piece at: ").strip().upper()
        if not re.match(r"[A-H][1-8]", selection_string):
            print "That's not a square (e.g. A1)"
            break
        file_letter = selection_string[0]
        rank_number = selection_string[1]
        coords = board.get_coords_for_grid_ref(file_letter, rank_number)
        piece = board.get_piece_at(coords)
        if not piece:
            print "No piece at %s" % selection_string
            break
        if not piece.color == WHITE:
            print "That's not your %s!" % piece.name
            break
        
        # Move the piece
        print board.get_string_rep()
        move_string = raw_input("Move the %s to: " % piece.name).strip().upper()
        if not re.match(r"[A-H][1-8]", selection_string):
            print "That's not a square (e.g. A1)"
            break
        file_letter = move_string[0]
        rank_number = move_string[1]
        coords = board.get_coords_for_grid_ref(file_letter, rank_number)
        if not coords in piece.get_valid_moves():
            print "That %s can't move to %s" % (piece.name, move_string)
            break
        
        board.move_piece_to(piece, coords)

if __name__ == "__main__":
    main()