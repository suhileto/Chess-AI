# coding=utf-8


import pygame
from pygame.locals import *
import copy
import pickle
import random
from collections import defaultdict
from collections import Counter
import threading  # GUI ile tahta olusurken AI'nın ayni anda dusunmesine izin vermek.
import os


class oyunBilgileri:
    def __init__(self, tahta, oyuncu, rok, gec_almak, HMC, history={}):
        self.board = tahta  # Parça kayıtları hakkında bilgi içeren bir 2B dizi. Böyle bir gösterim örneğini görmek için ana işlevi kontrol edin.
        self.player = oyuncu  # Taşınacak tarafı kaydeder. Oynamak için beyaz ise 0'a eşittir. Oynamak için siyahsa 1'i depolar.
        self.castling = rok  # Rok hakkini tutar
        self.EnP = gec_almak
        self.HMC = HMC
        self.history = history

    def getboard(self):
        return self.board

    def setboard(self, board):
        self.board = board

    def getplayer(self):
        return self.player

    def setplayer(self, player):
        self.player = player

    def getCastleRights(self):
        return self.castling

    def setCastleRights(self, castling_rights):
        self.castling = castling_rights

    def getEnP(self):
        return self.EnP

    def setEnP(self, EnP_Target):
        self.EnP = EnP_Target

    def getHMC(self):
        return self.HMC

    def setHMC(self, HMC):
        self.HMC = HMC

    def checkRepition(self):
        return any(value >= 3 for value in self.history.itervalues())

    def addtoHistory(self, position):
        # Mevcut konumdan benzersiz bir anahtar olustur:

        key = pos2key(position)
        #sözlüğe ekle.
        self.history[key] = self.history.get(key, 0) + 1

    def gethistory(self):
        return self.history

    def clone(self):
        clone = oyunBilgileri(copy.deepcopy(self.board),  # Independent copy
                              self.player,
                              copy.deepcopy(self.castling),  # Independent copy
                              self.EnP,
                              self.HMC)
        return clone


class golgeler:
    def __init__(self, resim, coord):
        self.image = resim
        self.pos = coord
    def getInfo(self):
        return [self.image, self.pos]


class Tas:
    def __init__(self, tasbilgi, satranc_koord):
        # tasbilgi 'Qb' gibi bir dizedir. Q, Kraliçe'yi ve b'yi temsil eder.
        tas = tasbilgi[0]
        color = tasbilgi[1]

        # Bu parça için görüntünün nerede saklandığı hakkında bilgi edinme
        # square_width ve square_height, üzerindeki karenin boyutunu temsil eder
        # satranç tahtası.
        if tas == 'K':
            index = 0
        elif tas == 'Q':
            index = 1
        elif tas == 'B':
            index = 2
        elif tas == 'N':
            index = 3
        elif tas == 'R':
            index = 4
        elif tas == 'P':
            index = 5
        left_x = square_width * index
        if color == 'w':
            left_y = 0
        else:
            left_y = square_height

        self.pieceinfo = tasbilgi
        # alt bölüm, hareketli grafik görüntüsünün parçamızı temsil eden bölümünü tanımlar:

        self.subsection = (left_x, left_y, square_width, square_height)

        self.chess_coord = satranc_koord
        self.pos = (-1, -1)


    def getInfo(self):
        return [self.chess_coord, self.subsection, self.pos]

    def setpos(self, pos):
        self.pos = pos

    def getpos(self):
        return self.pos

    def setcoord(self, coord):
        self.chess_coord = coord

    def __repr__(self):
        # useful for debugging
        return self.pieceinfo + '(' + str(chess_coord[0]) + ',' + str(chess_coord[1]) + ')'



#SATRANÇ İŞLEME FONKSİYONLARI



def isOccupied(board, x, y):# Tahtada belirli bir koordinat döndürür
    if board[y][x] == 0:
        #satranc tahtasının  üzerinde hiçbir şey yok.

        return False
    return True


def isOccupiedby(board, x, y, color):#Koordinatlar tarafından belirtilen özel renge göre true ya da false döndürür

    if board[y][x] == 0:

        return False
    if board[y][x][1] == color[0]:

        return True


    return False


def filterbyColor(board, listofTuples, color):
    filtered_list = []
    # Her koordinatı gözden geçirme:
    for pos in listofTuples:
        x = pos[0]
        y = pos[1]
        if x >= 0 and x <= 7 and y >= 0 and y <= 7 and not isOccupiedby(board, x, y, color):

            filtered_list.append(pos)
    return filtered_list


def lookfor(board, piece):
    listofLocations = []
    for row in range(8):
        for col in range(8):
            if board[row][col] == piece:
                x = col
                y = row
                listofLocations.append((x, y))
    return listofLocations


def isAttackedby(position, target_x, target_y, color):

    board = position.getboard()
    color = color[0]
    listofAttackedSquares = []
    for x in range(8):
        for y in range(8):
            if board[y][x] != 0 and board[y][x][1] == color:
                listofAttackedSquares.extend(
                    findPossibleSquares(position, x, y, True))

    return (target_x, target_y) in listofAttackedSquares


def findPossibleSquares(position, x, y, AttackSearch=False):

    board = position.getboard()
    player = position.getplayer()
    castling_rights = position.getCastleRights()
    EnP_Target = position.getEnP()

    if len(board[y][x]) != 2:
        return []
    piece = board[y][x][0]
    color = board[y][x][1]
    enemy_color = opp(color)
    listofTuples = []

    if piece == 'P':
        if color == 'w':
            if not isOccupied(board, x, y - 1) and not AttackSearch:

                listofTuples.append((x, y - 1))

                if y == 6 and not isOccupied(board, x, y - 2):

                    listofTuples.append((x, y - 2))

            if x != 0 and isOccupiedby(board, x - 1, y - 1, 'black'):

                listofTuples.append((x - 1, y - 1))
            if x != 7 and isOccupiedby(board, x + 1, y - 1, 'black'):

                listofTuples.append((x + 1, y - 1))
            if EnP_Target != -1:
                if EnP_Target == (x - 1, y - 1) or EnP_Target == (x + 1, y - 1):

                    listofTuples.append(EnP_Target)

        elif color == 'b':
            if not isOccupied(board, x, y + 1) and not AttackSearch:
                listofTuples.append((x, y + 1))
                if y == 1 and not isOccupied(board, x, y + 2):
                    listofTuples.append((x, y + 2))
            if x != 0 and isOccupiedby(board, x - 1, y + 1, 'white'):
                listofTuples.append((x - 1, y + 1))
            if x != 7 and isOccupiedby(board, x + 1, y + 1, 'white'):
                listofTuples.append((x + 1, y + 1))
            if EnP_Target == (x - 1, y + 1) or EnP_Target == (x + 1, y + 1):
                listofTuples.append(EnP_Target)

    elif piece == 'R':

        for i in [-1, 1]:

            kx = x
            while True:
                kx = kx + i
                if kx <= 7 and kx >= 0:

                    if not isOccupied(board, kx, y):

                        listofTuples.append((kx, y))
                    else:

                        if isOccupiedby(board, kx, y, enemy_color):
                            listofTuples.append((kx, y))

                        break

                else:
                    break

        for i in [-1, 1]:
            ky = y
            while True:
                ky = ky + i
                if ky <= 7 and ky >= 0:
                    if not isOccupied(board, x, ky):
                        listofTuples.append((x, ky))
                    else:
                        if isOccupiedby(board, x, ky, enemy_color):
                            listofTuples.append((x, ky))
                        break
                else:
                    break

    elif piece == 'N':
        for dx in [-2, -1, 1, 2]:
            if abs(dx) == 1:
                sy = 2
            else:
                sy = 1
            for dy in [-sy, +sy]:
                listofTuples.append((x + dx, y + dy))

        listofTuples = filterbyColor(board, listofTuples, color)
    elif piece == 'B':

        for dx in [-1, 1]:
            for dy in [-1, 1]:
                kx = x
                ky = y
                while True:
                    kx = kx + dx
                    ky = ky + dy
                    if kx <= 7 and kx >= 0 and ky <= 7 and ky >= 0:
                        if not isOccupied(board, kx, ky):
                            listofTuples.append((kx, ky))
                        else:
                            if isOccupiedby(board, kx, ky, enemy_color):
                                listofTuples.append((kx, ky))

                            break
                    else:

                        break

    elif piece == 'Q':  # A queen

        board[y][x] = 'R' + color
        list_rook = findPossibleSquares(position, x, y, True)

        board[y][x] = 'B' + color
        list_bishop = findPossibleSquares(position, x, y, True)

        listofTuples = list_rook + list_bishop
        board[y][x] = 'Q' + color
    elif piece == 'K':  # A king!

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                listofTuples.append((x + dx, y + dy))

        listofTuples = filterbyColor(board, listofTuples, color)
        if not AttackSearch:

            right = castling_rights[player]

            if (right[0] and
                    board[y][7] != 0 and
                    board[y][7][0] == 'R' and
                    not isOccupied(board, x + 1, y) and
                    not isOccupied(board, x + 2, y) and
                    not isAttackedby(position, x, y, enemy_color) and
                    not isAttackedby(position, x + 1, y, enemy_color) and
                    not isAttackedby(position, x + 2, y, enemy_color)):
                listofTuples.append((x + 2, y))
            # Queenside
            if (right[1] and
                    board[y][0] != 0 and
                    board[y][0][0] == 'R' and
                    not isOccupied(board, x - 1, y) and
                    not isOccupied(board, x - 2, y) and
                    not isOccupied(board, x - 3, y) and
                    not isAttackedby(position, x, y, enemy_color) and
                    not isAttackedby(position, x - 1, y, enemy_color) and
                    not isAttackedby(position, x - 2, y, enemy_color)):
                listofTuples.append((x - 2, y))


    if not AttackSearch:
        new_list = []
        for tupleq in listofTuples:
            x2 = tupleq[0]
            y2 = tupleq[1]
            temp_pos = position.clone()
            makemove(temp_pos, x, y, x2, y2)
            if not isCheck(temp_pos, color):
                new_list.append(tupleq)
        listofTuples = new_list
    return listofTuples


def makemove(position, x, y, x2, y2):
    board = position.getboard()
    piece = board[y][x][0]
    color = board[y][x][1]

    player = position.getplayer()
    castling_rights = position.getCastleRights()
    EnP_Target = position.getEnP()
    half_move_clock = position.getHMC()

    if isOccupied(board, x2, y2) or piece == 'P':

        half_move_clock = 0
    else:

        half_move_clock += 1


    board[y2][x2] = board[y][x]
    board[y][x] = 0

    if piece == 'K':

        castling_rights[player] = [False, False]

        if abs(x2 - x) == 2:
            if color == 'w':
                l = 7
            else:
                l = 0

            if x2 > x:
                board[l][5] = 'R' + color
                board[l][7] = 0
            else:
                board[l][3] = 'R' + color
                board[l][0] = 0

    if piece == 'R':

        if x == 0 and y == 0:

            castling_rights[1][1] = False
        elif x == 7 and y == 0:

            castling_rights[1][0] = False
        elif x == 0 and y == 7:

            castling_rights[0][1] = False
        elif x == 7 and y == 7:

            castling_rights[0][0] = False

    if piece == 'P':

        if EnP_Target == (x2, y2):
            if color == 'w':
                board[y2 + 1][x2] = 0
            else:
                board[y2 - 1][x2] = 0

        if abs(y2 - y) == 2:
            EnP_Target = (x, (y + y2) / 2)
        else:
            EnP_Target = -1

        if y2 == 0:
            board[y2][x2] = 'Qw'
        elif y2 == 7:
            board[y2][x2] = 'Qb'
    else:

        EnP_Target = -1


    player = 1 - player

    position.setplayer(player)
    position.setCastleRights(castling_rights)
    position.setEnP(EnP_Target)
    position.setHMC(half_move_clock)


def opp(color):
    color = color[0]
    if color == 'w':
        oppcolor = 'b'
    else:
        oppcolor = 'w'
    return oppcolor


def isCheck(position, color):

    board = position.getboard()
    color = color[0]
    enemy = opp(color)
    piece = 'K' + color

    x, y = lookfor(board, piece)[0]

    return isAttackedby(position, x, y, enemy)


def sahMat(position, color=-1):
    if color == -1:
        return sahMat(position, 'white') or sahMat(position, 'b')
    color = color[0]
    if isCheck(position, color) and allMoves(position, color) == []:

        return True

    return False


def isStalemate(position):

    player = position.getplayer()

    if player == 0:
        color = 'w'
    else:
        color = 'b'
    if not isCheck(position, color) and allMoves(position, color) == []:

        return True
    return False


def getallpieces(position, color):
    # Get the board:
    board = position.getboard()
    listofpos = []
    for j in range(8):
        for i in range(8):
            if isOccupiedby(board, i, j, color):
                listofpos.append((i, j))
    return listofpos


def allMoves(position, color):

    if color == 1:
        color = 'white'
    elif color == -1:
        color = 'black'
    color = color[0]

    listofpieces = getallpieces(position, color)
    moves = []

    for pos in listofpieces:

        targets = findPossibleSquares(position, pos[0], pos[1])
        for target in targets:

            moves.append([pos, target])
    return moves


def pos2key(position):

    board = position.getboard()

    boardTuple = []
    for row in board:
        boardTuple.append(tuple(row))
    boardTuple = tuple(boardTuple)

    rights = position.getCastleRights()

    tuplerights = (tuple(rights[0]), tuple(rights[1]))

    key = (boardTuple, position.getplayer(),
           tuplerights)

    return key


##############################////////GUI \\\\\\\\\\\\\#############################
def chess_coord_to_pixels(chess_coord):
    x, y = chess_coord

    if isAI:
        if AIPlayer == 0:

            return ((7 - x) * square_width, (7 - y) * square_height)
        else:
            return (x * square_width, y * square_height)

    if not isFlip or oyuncu == 0 ^ isTransition:
        return (x * square_width, y * square_height)
    else:
        return ((7 - x) * square_width, (7 - y) * square_height)


def pixel_coord_to_chess(pixel_coord):
    x, y = pixel_coord[0] / square_width, pixel_coord[1] / square_height

    if isAI:
        if AIPlayer == 0:
            return (7 - x, 7 - y)
        else:
            return (x, y)
    if not isFlip or oyuncu == 0 ^ isTransition:
        return (x, y)
    else:
        return (7 - x, 7 - y)


def getPiece(chess_coord):
    for piece in listofWhitePieces + listofBlackPieces:

        if piece.getInfo()[0] == chess_coord:
            return piece


def createPieces(board):

    listofWhitePieces = []
    listofBlackPieces = []

    for i in range(8):
        for k in range(8):
            if board[i][k] != 0:

                p = Tas(board[i][k], (k, i))

                if board[i][k][1] == 'w':
                    listofWhitePieces.append(p)
                else:
                    listofBlackPieces.append(p)

    return [listofWhitePieces, listofBlackPieces]


def createShades(listofTuples):
    global listofShades

    listofShades = []
    if isTransition:

        return
    if isDraw:

        coord = lookfor(tahta, 'Kw')[0]
        shade = golgeler(circle_image_yellow, coord)
        listofShades.append(shade)
        coord = lookfor(tahta, 'Kb')[0]
        shade = golgeler(circle_image_yellow, coord)
        listofShades.append(shade)

        return
    if oyunBitimi:

        coord = lookfor(tahta, 'K' + winner)[0]
        shade = golgeler(circle_image_green_big, coord)
        listofShades.append(shade)

    if isCheck(position, 'white'):
        coord = lookfor(tahta, 'Kw')[0]
        shade = golgeler(circle_image_red, coord)
        listofShades.append(shade)
    if isCheck(position, 'black'):
        coord = lookfor(tahta, 'Kb')[0]
        shade = golgeler(circle_image_red, coord)
        listofShades.append(shade)

    for pos in listofTuples:

        if isOccupied(tahta, pos[0], pos[1]):
            img = circle_image_capture
        else:
            img = circle_image_green
        shade = golgeler(img, pos)

        listofShades.append(shade)


def drawBoard():

    screen.blit(arkaplan, (0, 0))

    if oyuncu == 1:
        order = [listofWhitePieces, listofBlackPieces]
    else:
        order = [listofBlackPieces, listofWhitePieces]
    if isTransition:

        order = list(reversed(order))

    if isDraw or oyunBitimi or isAIThink:

        for shade in listofShades:
            img, chess_coord = shade.getInfo()
            pixel_coord = chess_coord_to_pixels(chess_coord)
            screen.blit(img, pixel_coord)

    if prevMove[0] != -1 and not isTransition:
        x, y, x2, y2 = prevMove
        screen.blit(yellowbox_image, chess_coord_to_pixels((x, y)))
        screen.blit(yellowbox_image, chess_coord_to_pixels((x2, y2)))




    for piece in order[0]:

        chess_coord, subsection, pos = piece.getInfo()
        pixel_coord = chess_coord_to_pixels(chess_coord)
        if pos == (-1, -1):

            screen.blit(pieces_image, pixel_coord, subsection)
        else:

            screen.blit(pieces_image, pos, subsection)

    if not (isDraw or oyunBitimi or isAIThink):
        for shade in listofShades:
            img, chess_coord = shade.getInfo()
            pixel_coord = chess_coord_to_pixels(chess_coord)
            screen.blit(img, pixel_coord)

    for piece in order[1]:
        chess_coord, subsection, pos = piece.getInfo()
        pixel_coord = chess_coord_to_pixels(chess_coord)
        if pos == (-1, -1):

            screen.blit(pieces_image, pixel_coord, subsection)
        else:

            screen.blit(pieces_image, pos, subsection)


###########################////////YAPAY ZEKA\\\\\\\\\\############################

def negamax(poz, derinlik, alfa, beta, hangi_oyuncu, oynanacak_hamle, root=True):
    # Öncelikle konumun  sözlükte kayıtlı olup olmadığını kontrol etm:

    if root:
        # Mevcut konumdan anahtar üret:
        key = pos2key(poz)
        if key in openings:
            # Oynatılacak en iyi hamleyi döndür:
            oynanacak_hamle[:] = random.choice(openings[key])
            return


    global searched

    if derinlik == 0:
        return hangi_oyuncu * analiz(poz)

    moves = allMoves(poz, hangi_oyuncu)

    if moves == []:
        return hangi_oyuncu * analiz(poz)

    if root:
        bestMove = moves[0]

    bestValue = -100000

    for move in moves:

        newpos = poz.clone()
        makemove(newpos, move[0][0], move[0][1], move[1][0], move[1][1])

        key = pos2key(newpos)

        if key in searched:
            value = searched[key]
        else:
            value = -negamax(newpos, derinlik - 1, -beta, -alfa, -hangi_oyuncu, [], False)
            searched[key] = value

        if value > bestValue:

            bestValue = value

            if root:
                bestMove = move

        alfa = max(alfa, value)
        if alfa >= beta:

            break

    if root:
        searched = {}
        oynanacak_hamle[:] = bestMove
        return

    return bestValue


def analiz(durum):
    if sahMat(durum, 'white'):
        # Siyah icin avantaj
        return -20000
    if sahMat(durum, 'black'):
        # Beyaz icin avantaj
        return 20000
    board = durum.getboard()
    # Daha hizli hesaplamalar icin tahtayi 1D dizisine cevirme:
    duz_tahta = [x for row in board for x in row]
    # Duz tahtaya degerleri atama
    c = Counter(duz_tahta)
    Qw = c['Qw']
    Qb = c['Qb']
    Rw = c['Rw']
    Rb = c['Rb']
    Bw = c['Bw']
    Bb = c['Bb']
    Nw = c['Nw']
    Nb = c['Nb']
    Pw = c['Pw']
    Pb = c['Pb']


    whiteMaterial = 9 * Qw + 5 * Rw + 3 * Nw + 3 * Bw + 1 * Pw
    blackMaterial = 9 * Qb + 5 * Rb + 3 * Nb + 3 * Bb + 1 * Pb
    numofmoves = len(durum.gethistory())
    gamephase = 'opening'
    if numofmoves > 40 or (whiteMaterial < 14 and blackMaterial < 14):
        gamephase = 'ending'

    Dw = doubledPawns(board, 'white')
    Db = doubledPawns(board, 'black')
    Sw = blockedPawns(board, 'white')
    Sb = blockedPawns(board, 'black')
    Iw = isolatedPawns(board, 'white')
    Ib = isolatedPawns(board, 'black')

    evaluation1 = 900 * (Qw - Qb) + 500 * (Rw - Rb) + 330 * (Bw - Bb
                                                             ) + 320 * (Nw - Nb) + 100 * (Pw - Pb) + -30 * (
                              Dw - Db + Sw - Sb + Iw - Ib
                              )

    evaluation2 = pieceSquareTable(duz_tahta, gamephase)

    evaluation = evaluation1 + evaluation2

    return evaluation


def pieceSquareTable(flatboard, gamephase):

    score = 0

    for i in range(64):
        if flatboard[i] == 0:

            continue

        piece = flatboard[i][0]
        color = flatboard[i][1]
        sign = +1

        if color == 'b':
            i = (7 - i / 8) * 8 + i % 8
            sign = -1

        if piece == 'P':
            score += sign * pawn_table[i]
        elif piece == 'N':
            score += sign * knight_table[i]
        elif piece == 'B':
            score += sign * bishop_table[i]
        elif piece == 'R':
            score += sign * rook_table[i]
        elif piece == 'Q':
            score += sign * queen_table[i]
        elif piece == 'K':

            if gamephase == 'opening':
                score += sign * king_table[i]
            else:
                score += sign * king_endgame_table[i]
    return score


def doubledPawns(board, color):
    color = color[0]

    listofpawns = lookfor(board, 'P' + color)

    repeats = 0
    temp = []
    for pawnpos in listofpawns:
        if pawnpos[0] in temp:
            repeats = repeats + 1
        else:
            temp.append(pawnpos[0])
    return repeats


def blockedPawns(board, color):
    color = color[0]
    listofpawns = lookfor(board, 'P' + color)
    blocked = 0
    # Self explanatory:
    for pawnpos in listofpawns:
        if ((color == 'w' and isOccupiedby(board, pawnpos[0], pawnpos[1] - 1,
                                           'black'))
                or (color == 'b' and isOccupiedby(board, pawnpos[0], pawnpos[1] + 1,
                                                  'white'))):
            blocked = blocked + 1
    return blocked


def isolatedPawns(board, color):
    color = color[0]
    listofpawns = lookfor(board, 'P' + color)
    # Get x coordinates of all the pawns:
    xlist = [x for (x, y) in listofpawns]
    isolated = 0
    for x in xlist:
        if x != 0 and x != 7:
            # For non-edge cases:
            if x - 1 not in xlist and x + 1 not in xlist:
                isolated += 1
        elif x == 0 and 1 not in xlist:
            # Left edge:
            isolated += 1
        elif x == 7 and 6 not in xlist:
            # Right edge:
            isolated += 1
    return isolated


#*****************Main Fonkisyonu
tahta = [['Rb', 'Nb', 'Bb', 'Qb', 'Kb', 'Bb', 'Nb', 'Rb'],
         ['Pb', 'Pb', 'Pb', 'Pb', 'Pb', 'Pb', 'Pb', 'Pb'],
         [0, 0, 0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 0, 0],
         [0, 0, 0, 0, 0, 0, 0, 0],
         ['Pw', 'Pw', 'Pw', 'Pw', 'Pw', 'Pw', 'Pw', 'Pw'],
         ['Rw', 'Nw', 'Bw', 'Qw', 'Kw', 'Bw', 'Nw', 'Rw']]



oyuncu = 0  # Bu bir sonraki hamleyi yapan oyuncu. 0 beyaz, 1 siyah
rok_hakki = [[True, True], [True, True]]
En_Passant_Target = -1 # Gecerken alma hamlesi varsa koordinati tutar.Yoksa -1'i tutar
half_move_clock = 0  # Simdiye kadar oynanan ters cevrilebilir hamlelerin sayisini saklar.
position = oyunBilgileri(tahta, oyuncu, rok_hakki, En_Passant_Target
                         , half_move_clock)
# fonksiyonunun kullanacagi degiskenler:
pawn_table = [0, 0, 0, 0, 0, 0, 0, 0,
              50, 50, 50, 50, 50, 50, 50, 50,
              10, 10, 20, 30, 30, 20, 10, 10,
              5, 5, 10, 25, 25, 10, 5, 5,
              0, 0, 0, 20, 20, 0, 0, 0,
              5, -5, -10, 0, 0, -10, -5, 5,
              5, 10, 10, -20, -20, 10, 10, 5,
              0, 0, 0, 0, 0, 0, 0, 0]
knight_table = [-50, -40, -30, -30, -30, -30, -40, -50,
                -40, -20, 0, 0, 0, 0, -20, -40,
                -30, 0, 10, 15, 15, 10, 0, -30,
                -30, 5, 15, 20, 20, 15, 5, -30,
                -30, 0, 15, 20, 20, 15, 0, -30,
                -30, 5, 10, 15, 15, 10, 5, -30,
                -40, -20, 0, 5, 5, 0, -20, -40,
                -50, -90, -30, -30, -30, -30, -90, -50]
bishop_table = [-20, -10, -10, -10, -10, -10, -10, -20,
                -10, 0, 0, 0, 0, 0, 0, -10,
                -10, 0, 5, 10, 10, 5, 0, -10,
                -10, 5, 5, 10, 10, 5, 5, -10,
                -10, 0, 10, 10, 10, 10, 0, -10,
                -10, 10, 10, 10, 10, 10, 10, -10,
                -10, 5, 0, 0, 0, 0, 5, -10,
                -20, -10, -90, -10, -10, -90, -10, -20]
rook_table = [0, 0, 0, 0, 0, 0, 0, 0,
              5, 10, 10, 10, 10, 10, 10, 5,
              -5, 0, 0, 0, 0, 0, 0, -5,
              -5, 0, 0, 0, 0, 0, 0, -5,
              -5, 0, 0, 0, 0, 0, 0, -5,
              -5, 0, 0, 0, 0, 0, 0, -5,
              -5, 0, 0, 0, 0, 0, 0, -5,
              0, 0, 0, 5, 5, 0, 0, 0]
queen_table = [-20, -10, -10, -5, -5, -10, -10, -20,
               -10, 0, 0, 0, 0, 0, 0, -10,
               -10, 0, 5, 5, 5, 5, 0, -10,
               -5, 0, 5, 5, 5, 5, 0, -5,
               0, 0, 5, 5, 5, 5, 0, -5,
               -10, 5, 5, 5, 5, 5, 0, -10,
               -10, 0, 5, 0, 0, 0, 0, -10,
               -20, -10, -10, 70, -5, -10, -10, -20]
king_table = [-30, -40, -40, -50, -50, -40, -40, -30,
              -30, -40, -40, -50, -50, -40, -40, -30,
              -30, -40, -40, -50, -50, -40, -40, -30,
              -30, -40, -40, -50, -50, -40, -40, -30,
              -20, -30, -30, -40, -40, -30, -30, -20,
              -10, -20, -20, -20, -20, -20, -20, -10,
              20, 20, 0, 0, 0, 0, 20, 20,
              20, 30, 10, 0, 0, 10, 30, 20]
king_endgame_table = [-50, -40, -30, -20, -20, -30, -40, -50,
                      -30, -20, -10, 0, 0, -10, -20, -30,
                      -30, -10, 20, 30, 30, 20, -10, -30,
                      -30, -10, 30, 40, 40, 30, -10, -30,
                      -30, -10, 30, 40, 40, 30, -10, -30,
                      -30, -10, 20, 30, 30, 20, -10, -30,
                      -30, -30, 0, 0, 0, 0, -30, -30,
                      -50, -30, -30, -30, -30, -30, -30, -50]

#  GUI:
#  pygame baslatma
pygame.init()

screen = pygame.display.set_mode((600, 600))


arkaplan = pygame.image.load(os.path.join('Media', 'chessboard.png')).convert()

pieces_image = pygame.image.load(os.path.join('Media', 'Chess_Pieces_Sprite.png')).convert_alpha()
circle_image_green = pygame.image.load(os.path.join('Media', 'green_circle_small.png')).convert_alpha()
circle_image_capture = pygame.image.load(os.path.join('Media', 'green_circle_neg.png')).convert_alpha()
circle_image_red = pygame.image.load(os.path.join('Media', 'red_circle_big.png')).convert_alpha()
greenbox_image = pygame.image.load(os.path.join('Media', 'green_box.png')).convert_alpha()
circle_image_yellow = pygame.image.load(os.path.join('Media', 'yellow_circle_big.png')).convert_alpha()
circle_image_green_big = pygame.image.load(os.path.join('Media', 'green_circle_big.png')).convert_alpha()
yellowbox_image = pygame.image.load(os.path.join('Media', 'yellow_box.png')).convert_alpha()

withfriend_pic = pygame.image.load(os.path.join('Media', 'ARKADAŞ.png')).convert_alpha()
withAI_pic = pygame.image.load(os.path.join('Media', 'ARR.png')).convert_alpha()
playwhite_pic = pygame.image.load(os.path.join('Media', 'BEYZA.png')).convert_alpha()
playblack_pic = pygame.image.load(os.path.join('Media', 'SIYAH.png')).convert_alpha()
flipEnabled_pic = pygame.image.load(os.path.join('Media', 'BEYZ.png')).convert_alpha()
flipDisabled_pic = pygame.image.load(os.path.join('Media', 'ÇEVİRME.png')).convert_alpha()

# Boyutlari alma:
# Arka plan boyutunu al:
size_of_bg = arkaplan.get_rect().size

# Tek tek karelerin boyutunu alma
square_width = size_of_bg[0] / 8
square_height = size_of_bg[1] / 8

# Her parçanın bir kareye sığması için görüntüleri yeniden ölçeklendirin:
pieces_image = pygame.transform.scale(pieces_image,
                                      (square_width * 6, square_height * 2))
circle_image_green = pygame.transform.scale(circle_image_green,
                                            (square_width, square_height))
circle_image_capture = pygame.transform.scale(circle_image_capture,
                                              (square_width, square_height))
circle_image_red = pygame.transform.scale(circle_image_red,
                                          (square_width, square_height))
greenbox_image = pygame.transform.scale(greenbox_image,
                                        (square_width, square_height))
yellowbox_image = pygame.transform.scale(yellowbox_image,
                                         (square_width, square_height))
circle_image_yellow = pygame.transform.scale(circle_image_yellow,
                                             (square_width, square_height))
circle_image_green_big = pygame.transform.scale(circle_image_green_big,
                                                (square_width, square_height))
withfriend_pic = pygame.transform.scale(withfriend_pic,
                                        (square_width * 4, square_height * 4))
withAI_pic = pygame.transform.scale(withAI_pic,
                                    (square_width * 4, square_height * 4))
playwhite_pic = pygame.transform.scale(playwhite_pic,
                                       (square_width * 4, square_height * 4))
playblack_pic = pygame.transform.scale(playblack_pic,
                                       (square_width * 4, square_height * 4))
flipEnabled_pic = pygame.transform.scale(flipEnabled_pic,
                                         (square_width * 4, square_height * 4))
flipDisabled_pic = pygame.transform.scale(flipDisabled_pic,
                                          (square_width * 4, square_height * 4))


# Arka planla aynı boyutta bir pencere oluşturun, başlığını ayarlayın ve
# arka plan resmini üzerine yükleyin (tahta):
screen = pygame.display.set_mode(size_of_bg)
pygame.display.set_caption('Satranc Oyunu')
screen.blit(arkaplan, (0, 0))


# Tahtaya çizilmesi gereken parçaların bir listesini oluşturun:
listofWhitePieces, listofBlackPieces = createPieces(tahta)

# Gölgeler listesini başlatın:
listofShades = []

clock = pygame.time.Clock()
isDown = False # Farenin basılı tutulup tutulmadığını gösteren değişken

isClicked = False # Bir parçanın sırayla tıklanıp tıklanmadığını takip etmek için

isTransition = False# kullanıcının hareket etme niyetini gösterir.

isDraw = False# Bir parçanın oynatıp oynatılmadığının kaydını tutar.

oyunBitimi = False# Oyun berabere biterse True saklanır
# Satranç oyunu şah mat, çıkmaz vb. İle sona erdiğinde Gerçekleşecek.
isRecord = False
isAIThink = False# AI'nın oynanacak en iyi hamleyi hesaplayıp hesaplamadığını kaydeder.

openings = defaultdict(list)

try:
    file_handle = open('openingTable.txt', 'r+')
    openings = pickle.loads(file_handle.read())
except:
    if isRecord:
        file_handle = open('openingTable.txt', 'w')

searched = {}  # Negamax'ın sahip olduğu düğümleri takip etmesini sağlayan global değişken
# zaten değerlendirildi.
prevMove = [-1, -1, -1, -1]  # Ayrıca oynatılan son hamleyi saklayan global  değişken,
# drawBoard () öğesinin karelerde Gölgeler oluşturmasına izin verin.

ax, ay = 0, 0
numm = 0

# Menüyü göstermek ve kullanıcı seçeneklerini takip etmek için:
isMenu = True
isAI = -1
isFlip = -1
AIPlayer = -1

# Son olarak, kullanıcı çıkmak isteyene kadar false olarak saklanacak bir değişken:
oyunBitimi = False

# Kullanıcı uygulamadan çıkana kadar program bu döngüde kalır
while not oyunBitimi:
    LEFT = 1
    SCROLL = 2
    RIGHT = 3

    if isMenu:

        # Menünün şu anda gösterilmesi gerekiyor.
        screen.blit(arkaplan, (0, 0))
        if isAI == -1:

            # Kullanıcı yapay zekaya karşı
            # veya bir arkadaşa karşı oynamayı seçmedi.

            screen.blit(withfriend_pic, (0, square_height * 2))
            screen.blit(withAI_pic, (square_width * 4, square_height * 2))
        elif isAI == True:
            # Kullanıcı yapay zekaya karşı oynamayı seçti.
            # Kullanıcının beyaz veya siyah olarak oynamasını seçmesi:
            screen.blit(playwhite_pic, (0, square_height * 2))
            screen.blit(playblack_pic, (square_width * 4, square_height * 2))
        elif isAI == False:

            # Kullanıcı bir arkadaşıyla oynamayı seçti.
            # Tahtayı çevirme veya tahtayı çevirme seçimine izin ver:
            screen.blit(flipDisabled_pic, (0, square_height * 2))
            screen.blit(flipEnabled_pic, (square_width * 4, square_height * 2))
        if isFlip != -1:

            # Tüm parçaları tahtaya çiz:
            drawBoard()

            # Menününyü görünmez yap:
            isMenu = False

            # Oyuncunun AI'ya karşı oynamayı seçmesi :
            if isAI and AIPlayer == 0:
                colorsign = 1
                bestMoveReturn = []
                move_thread = threading.Thread(target=negamax,args=(position, 3, -1000000, 1000000, colorsign, bestMoveReturn))
                move_thread.start()
                isAIThink = True
            continue
        for event in pygame.event.get():
            #Menüdeyken olayları yönetin:
            if event.type == QUIT:
                # Pencere kapatıldı.
                oyunBitimi = True
                break
            if event.type == MOUSEBUTTONUP :
                # Fare bir yere tıklandı.
                # Tıklamanın koordinatlarını alın:
                pos = pygame.mouse.get_pos()

                # Sol kutunun veya sağ kutunun tıklanıp tıklanmadığını belirleyin.
                # Daha sonra güncel bilgilere göre uygun bir eylem seçin
                # menü durumu:
                if (pos[0] < square_width * 4 and
                        pos[1] > square_height * 2 and
                        pos[1] < square_height * 6):

                    # SOL TIKLADI
                    if isAI == -1:
                        isAI = False
                    elif isAI == True:
                        AIPlayer = 1
                        isFlip = False
                    elif isAI == False:
                        isFlip = False
                elif (pos[0] > square_width * 4 and
                      pos[1] > square_height * 2 and
                      pos[1] < square_height * 6):
                    #SAG TIKLADI
                    if isAI == -1:
                        isAI = True
                    elif isAI == True:
                        AIPlayer = 0
                        isFlip = False
                    elif isAI == False:
                        isFlip = True


        pygame.display.update()


        clock.tick(60)
        continue
    # menü bölümü yapıldı.
    # Ai düşünüyorsa yesil kareler görünür
    numm += 1
    if isAIThink and numm % 6 == 0:
        ax += 1
        if ax == 8:
            ay += 1
            ax = 0
        if ay == 8:
            ax, ay = 0, 0
        if ax % 4 == 0:
            createShades([])

        if AIPlayer == 0:
            listofShades.append(golgeler(greenbox_image, (7 - ax, 7 - ay)))
        else:
            listofShades.append(golgeler(greenbox_image, (ax, ay)))

    for event in pygame.event.get():
        # Tüm kullanıcı girişleriyle ilgilenin:
        if event.type == QUIT:

            oyunBitimi = True

            break

        if oyunBitimi or isTransition or isAIThink:
            continue
        # isDown, bir parçanın sürüklendiği anlamına gelir.
        if not isDown and event.type == MOUSEBUTTONDOWN:

            # Fare basıldı.
            # Farenin koordinatlarını alın
            pos = pygame.mouse.get_pos()

            # satranç koordinatlarına dönüştür:
            chess_coord = pixel_coord_to_chess(pos)
            x = chess_coord[0]
            y = chess_coord[1]
            # Tıklanan parça kendi parçanız tarafından kullanılmıyorsa,
            # bu fare tıklamasını yoksay:
            if not isOccupiedby(tahta, x, y, 'wb'[oyuncu]):
                continue
            #Sürüklenmesi veya seçilmesi gereken parçaya referans alın:
            dragPiece = getPiece(chess_coord)

            # Bu parçanın saldırabileceği olası kareleri bulun:
            listofTuples = findPossibleSquares(position, x, y)
            #
            # Tüm bu kareleri vurgulayın:
            createShades(listofTuples)
            ## Kontrol edilen bir kral olmadığı sürece seçilen karede yeşil bir kutu görünmelidir,
            # bu durumda kralın üzerinde kırmızı bir renk olması nedeniyle olmamalıdır.
            if ((dragPiece.pieceinfo[0] == 'K') and
                    (isCheck(position, 'white') or isCheck(position, 'black'))):
                None
            else:
                listofShades.append(golgeler(greenbox_image, (x, y)))
            #parça sürükleniyor
            isDown = True
        if (isDown or isClicked) and event.type == MOUSEBUTTONUP:
            # Fare serbest bırakıldı
            isDown = False
            #
            # Parçayı tekrar koordinat konumuna getirin
            dragPiece.setpos((-1, -1))
            #
            # Koordinatları alın ve dönüştürün:
            pos = pygame.mouse.get_pos()
            chess_coord = pixel_coord_to_chess(pos)
            x2 = chess_coord[0]
            y2 = chess_coord[1]

            isTransition = False
            if (x, y) == (x2, y2):  #Surukleme YOK

                if not isClicked:  # daha önce hicbir seye tiklanmadi

                    # İlk tik
                    isClicked = True
                    prevPos = (x, y)

                else:  # Daha once bir sey tiklanmisti

                    # onceki tiklamanin yerini bulun:
                    x, y = prevPos
                    if (x, y) == (x2, y2):  # Kullanici ayni kareyi tekrar tikladi.

                        isClicked = False

                        createShades([])
                    else:
                        #
                        # Kullanıcı bu ikinci tıklamayla başka bir yeri tıkladı:
                        if isOccupiedby(tahta, x2, y2, 'wb'[oyuncu]):
                           # Kullanıcı kendi parçası tarafından işgal edilen bir kareyi tıklattı.Bu kendi parçanıza ilk tıklamayı yapmak gibidir:
                            isClicked = True
                            prevPos = (x2, y2)  # Store it
                        else:
                            # Kullanıcı geçerli bir hedef kareyi tıklamış veya tıklamamış olabilir.
                            isClicked = False
                            # Destory all shades
                            createShades([])
                            isTransition = True  # Muhtemelen taşıma geçerliyse.

            if not (x2, y2) in listofTuples:
                # Taşıma geçersiz
                isTransition = False
                continue
            #Buraya ulaşmak geçerli bir hamle seçildiği anlamına gelir. Kayıt seçeneği seçildiyse, hamleyi açılış sözlüğüne kaydedin:
            if isRecord:
                key = pos2key(position)
                # Zaten orada olmadığından emin olun:
                if [(x, y), (x2, y2)] not in openings[key]:
                    openings[key].append([(x, y), (x2, y2)])

            # Harekete gec:
            makemove(position, x, y, x2, y2)
            # Bu hareketi 'önceki' hareket (aslında en son hareket) olacak şekilde güncelleyin, böylece üzerinde sarı tonlar gösterilebilir.
            prevMove = [x, y, x2, y2]
            #
            # Hangi oyuncunun oynayacağını güncelle:
            oyuncu = position.getplayer()
            # Yeni konumu geçmişe ekleyin:

            position.addtoHistory(position)
            #  Tahtayi Cizme
            HMC = position.getHMC()
            if HMC >= 100 or isStalemate(position) or position.checkRepition():
                # There is a draw:
                isDraw = True
                oyunBitimi = True
            # Sah mat olup olmadigini kontrol etme:

            if sahMat(position, 'white'):
                winner = 'b'
                oyunBitimi = True
            if sahMat(position, 'black'):
                winner = 'w'
                oyunBitimi = True
            #AI seçeneği seçildiyse ve oyun hala bitmediyse,yapay zeka bir sonraki hamlesini düşünmeye başlasın:

            if isAI and not oyunBitimi:
                if oyuncu == 0:
                    colorsign = 1
                else:
                    colorsign = -1
                bestMoveReturn = []
                move_thread = threading.Thread(target=negamax,
                                               args=(position, 3, -1000000, 1000000, colorsign, bestMoveReturn))
                move_thread.start()
                isAIThink = True

            # Parçayı yeni yerine taşı:
            dragPiece.setcoord((x2, y2))



            if not isTransition:
                listofWhitePieces, listofBlackPieces = createPieces(tahta)
            else:
                movingPiece = dragPiece
                origin = chess_coord_to_pixels((x, y))
                destiny = chess_coord_to_pixels((x2, y2))
                movingPiece.setpos(origin)
                step = (destiny[0] - origin[0], destiny[1] - origin[1])


            # Her iki şekilde de gölgeler silinmelidir:
            createShades([])

    #  animasyonun gerçekleşmesi
    if isTransition:
        p, q = movingPiece.getpos()
        dx2, dy2 = destiny
        n = 30.0
        if abs(p - dx2) <= abs(step[0] / n) and abs(q - dy2) <= abs(step[1] / n):

            # tas hedefine ulaştı:
            movingPiece.setpos((-1, -1))
            #Birinin yakalanması durumunda yeni parçalistesi oluşturun:
            listofWhitePieces, listofBlackPieces = createPieces(tahta)

            isTransition = False
            createShades([])
        else:
            # Hedefine yaklaştırın

            movingPiece.setpos((p + step[0] / n, q + step[1] / n))
    # Bir parça sürükleniyorsa, sürükleyen parçanın fareyi takip etmesine izin verin:

    if isDown:
        m, k = pygame.mouse.get_pos()
        dragPiece.setpos((m - square_width / 2, k - square_height / 2))
    #AI düşünüyor
    if isAIThink and not isTransition:
        if not move_thread.isAlive():
            # AI bir karar verdi.
            # Artık düşünmüyor
            isAIThink = False
            # Destroy any shades:
            createShades([])
            # Hareket onerisi
            [x, y], [x2, y2] = bestMoveReturn
            #Her şeyi tıpkı kullanıcı tıklama hareketi ile hareket ettirmiş gibi yapın:
            makemove(position, x, y, x2, y2)
            prevMove = [x, y, x2, y2]
            oyuncu = position.getplayer()
            HMC = position.getHMC()
            position.addtoHistory(position)
            if HMC >= 100 or isStalemate(position) or position.checkRepition():
                isDraw = True
                oyunBitimi = True
            if sahMat(position, 'white'):
                winner = 'b'
                oyunBitimi = True
            if sahMat(position, 'black'):
                winner = 'w'
                oyunBitimi = True
            # Hareketi canlandırın:

            isTransition = True
            movingPiece = getPiece((x, y))
            origin = chess_coord_to_pixels((x, y))
            destiny = chess_coord_to_pixels((x2, y2))
            movingPiece.setpos(origin)
            step = (destiny[0] - origin[0], destiny[1] - origin[1])


    drawBoard()

    pygame.display.update()


    clock.tick(60)


pygame.quit()

if isRecord:
    file_handle.seek(0)
    pickle.dump(openings, file_handle)
    file_handle.truncate()
    file_handle.close()