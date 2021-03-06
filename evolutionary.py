#!/usr/bin/env python
#############
# Ankit Gupta and Aran Khanna
# CS 229r - Final Project
# 
# tic-tac-toe optimal solver implementation from http://cwoebker.com/posts/tic-tac-toe
# Implements evolutionary search - this was used for testing and debugging
#############################

# tic-tac-toe optimal solver implementation from http://cwoebker.com/posts/tic-tac-toe

import numpy as np
import random
from pybrain.datasets            import ClassificationDataSet
from pybrain.utilities           import percentError
from pybrain.tools.shortcuts     import buildNetwork
from pybrain.supervised.trainers import BackpropTrainer
from pybrain.structure.modules   import SoftmaxLayer
from pybrain.structure.modules   import TanhLayer
import cPickle as pickle

from multiprocessing import Pool
import multiprocessing

numGamesTraining = 1000
numEpochs = 5

# if usePriorNetwork = False, then the newly trained network will be saved in fileNameForNetworkSavingLoading
# if usePriorNetwor = True, then the network will be loaded from fileNameForNetworkSavingLoading
usePriorNetwork = False
usePriorDataset = True

# this can be used to save/load either the full trained network or just the dataset 
# to make the training phase faster
fileNameForNetworkSavingLoading = "trainednetwork_9_9"
fileNameForDataSavingLoading = "input_dataset_1000games"

# specify the setup of neurons per layer, and other arguments for the neural network
#inputlayers = [9, 30, 50, 30, 9]
inputargs = {'outclass': SoftmaxLayer, 'hiddenclass': TanhLayer}

class Tic(object):
    winning_combos = (
        [0, 1, 2], [3, 4, 5], [6, 7, 8],
        [0, 3, 6], [1, 4, 7], [2, 5, 8],
        [0, 4, 8], [2, 4, 6])

    winners = ('X-win', 'Draw', 'O-win')

    def __init__(self, squares=[]):
        if len(squares) == 0:
            self.squares = [None for i in range(9)]
        else:
            self.squares = squares

    def getBoard(self):
        newboard = []
        for x in self.squares:
            if x == 'X':
                newboard.append(1)
            elif x == 'O':
                newboard.append(-1)
            else:
                newboard.append(0)
        return newboard
    def show(self):
        for element in [self.squares[i:i + 3] for i in range(0, len(self.squares), 3)]:
            print element

    def available_moves(self):
        """what spots are left empty?"""
        return [k for k, v in enumerate(self.squares) if v is None]

    def available_combos(self, player):
        """what combos are available?"""
        return self.available_moves() + self.get_squares(player)

    def complete(self):
        """is the game over?"""
        if None not in [v for v in self.squares]:
            return True
        if self.winner() != None:
            return True
        return False

    def X_won(self):
        return self.winner() == 'X'

    def O_won(self):
        return self.winner() == 'O'

    def tied(self):
        return self.complete() == True and self.winner() is None

    def winner(self):
        for player in ('X', 'O'):
            positions = self.get_squares(player)
            for combo in self.winning_combos:
                win = True
                for pos in combo:
                    if pos not in positions:
                        win = False
                if win:
                    return player
        return None

    def get_squares(self, player):
        """squares that belong to a player"""
        return [k for k, v in enumerate(self.squares) if v == player]

    def make_move(self, position, player):
        """place on square on the board"""
        self.squares[position] = player

    def alphabeta(self, node, player, alpha, beta):
        if node.complete():
            if node.X_won():
                return -1
            elif node.tied():
                return 0
            elif node.O_won():
                return 1
        for move in node.available_moves():
            node.make_move(move, player)
            val = self.alphabeta(node, get_enemy(player), alpha, beta)
            node.make_move(move, None)
            if player == 'O':
                if val > alpha:
                    alpha = val
                if alpha >= beta:
                    return beta
            else:
                if val < beta:
                    beta = val
                if beta <= alpha:
                    return alpha
        if player == 'O':
            return alpha
        else:
            return beta


def determine(board, player):
    a = -2
    choices = []
    if len(board.available_moves()) == 9:
        return 4
    for move in board.available_moves():
        board.make_move(move, player)
        val = board.alphabeta(board, get_enemy(player), -2, 2)
        board.make_move(move, None)
        #print "move:", move + 1, "causes:", board.winners[val + 1]
        if val > a:
            a = val
            choices = [move]
        elif val == a:
            choices.append(move)
    #print choices
    return random.choice(choices)


def get_enemy(player):
    if player == 'X':
        return 'O'
    return 'X'

def to_feature_vector(board):
    vec = []
    for move in board.squares:
        if move is None:
            vec.append(0)
        elif move == 'X':
            vec.append(1)
        elif move == 'O':
            vec.append(2)
            
    return vec

def from_feature_vector(moves):
    vec = []
    for move in moves:
        if move == 0:
            vec.append(None)
        elif move == 1:
            vec.append('X')
        elif move == -1:
            vec.append('O')
            
    return vec

def mutate(config):
    newconf = []
    newconf.append(config[0])
    for elem in config[1:-1]:
        flip = np.random.binomial(1, .9)
        if flip == 0:
            newconf.append(np.random.randint(0, 50))
        else:
            newconf.append(elem)
    newconf.append(config[-1])
    return newconf


def crossOver(config1, config2):
    length = len(config1)
    newconfig = []
    for i in range(length):
        x = np.random.rand()
        if x < .5:
            newconfig.append(config1[i])
        else:
            newconfig.append(config2[i])
    return mutate(newconfig)

def createSimilarConfigurations(configs, numWanted):
    configs = configs.tolist()
    numconfigs = len(configs)

    # start the new configurations with the old ones
    newconfigs = configs

    # for the number that are left, repeatedly pick a random configuration and mutate it
    for i in range(numWanted - numconfigs):
        config = crossOver(configs[np.random.randint(0, numconfigs)], configs[np.random.randint(0, numconfigs)])
        #config = configs[np.random.randint(0, numconfigs)]
        newconfigs.append(config)

    return np.array(newconfigs)



def trainNetwork(inputlayers, args, numGamesForTraining, numEpochsForTraining):
    configs = []
    decisions = []
    layers = filter(lambda a: a != 0, inputlayers)
    #print layers
    
    # create a Feed-Forward Neural Network
    fnn = buildNetwork(*layers, **args)


    # Load the Network from Memory if desired
    if (usePriorNetwork):
        fileObject = open(fileNameForNetworkSavingLoading,'r')
        fnn = pickle.load(fileObject)

    # If not loading from memory, train the network
    else:
        
        if (usePriorDataset):
            fileObjectData = open(fileNameForDataSavingLoading,'r')
            dataset = pickle.load(fileObjectData)
            #print dataset
        else:
            # loop over all of the games
            for i in range(numGamesForTraining):
                # initialize a new game
                board = Tic()
                
                # loop until the game is complete
                while not board.complete():
                    player = 'X'
                    
                    # add the board configuration and resultant best-move to the training set
                    configs.append(board.getBoard())
                    player_move = determine(board, player)
                    decisions.append(player_move)
                    
                    # makes sure the player move is valid
                    if not player_move in board.available_moves():
                        continue
                    board.make_move(player_move, player)

                    if board.complete():
                        break
                    
                    # switch to the other player
                    player = get_enemy(player)

                    # add the board configuation and resultant best-move to the training set
                    configs.append(board.getBoard())
                    computer_move = determine(board, player)
                    decisions.append(computer_move)

                    board.make_move(computer_move, player)
                
                #print "winner is", board.winner()
        
            # create a classification dataset from the input values
            dataset = ClassificationDataSet(9, nb_classes=9)
            for i in range(len(configs)):
                dataset.appendLinked(configs[i], [decisions[i]])
            dataset._convertToOneOfMany()

            fileObjectData = open(fileNameForDataSavingLoading, 'w')
            pickle.dump(dataset, fileObjectData)
            fileObjectData.close()

        # use backpropogation to train the neural network
        trainer = BackpropTrainer( fnn, dataset=dataset, momentum=0.1, verbose=False, weightdecay=0.01)
        for i in range(numEpochsForTraining):
            trainer.trainEpochs(1)

        # print predictions on the training data- not actually used for anything
        prediction_moves = trainer.testOnClassData()

        # save the network to the specified file to save time later if not retraining
        fileObject = open(fileNameForNetworkSavingLoading, 'w')
        pickle.dump(fnn, fileObject)
        fileObject.close()

    return fnn

def testNetwork(numGames, fnn):
    configs = []
    decisions = []

    # In this stage, we play the ideal solver against the learned neural network, and count the number of draws, wins and losses
    # note, it is not possible to win against the computer - so really we are trying to find the number of draws
    winners = []
    #numGames = 100
    for i in range(numGames):
        board = Tic()
        
        # play until someone wins the game
        while not board.complete():
            player = 'X'
            #datasettmp = ClassificationDataSet(9, nb_classes=9)
            #datasettmp.appendLinked(board.getBoard(), [0])
            
            # get the activations for a given board state
            activation = fnn.activate(board.getBoard())
            activation = np.array(activation)

            # argsort activations from greatest to least
            order_of_attempts = np.argsort((-1)*activation)
            attempt = 0
            
            # keep picking moves from highest to least activation until an available one is found
            player_move = order_of_attempts[attempt]
            while player_move not in board.available_moves():
                attempt += 1
                player_move = order_of_attempts[attempt]

            #print player_move

            board.make_move(player_move, player)
            #board.show()

            if board.complete():
                break
            
            # let the computer make its move
            player = get_enemy(player)
            configs.append(board.getBoard())

            computer_move = determine(board, player)

            decisions.append(computer_move)

            board.make_move(computer_move, player)

        #print "winner is", board.winner()
        winners.append(board.winner())

    # calculate the number of wins for each
    Xwins = [win for win in winners if win == 'X']
    numXwins = len(Xwins)
    Owins = [win for win in winners if win == 'O']
    numOwins = len(Owins)

    #print "Number of times Neural Net won is ", numXwins, " out of ", numGames
    #print "Number of times Optimal Solver won is ", numOwins, " out of ", numGames
    #print "Number of Draws is ", numGames - numXwins - numOwins, " out of ", numGames
    return numGames - numXwins - numOwins

def trainAndTest(inputlayers, args, numGamesForTraining, numEpochsForTraining, numGames):
    #print inputlayers, args, numGamesForTraining, numEpochsForTraining, numGames
    fnn = trainNetwork(inputlayers, args, numGamesForTraining, numEpochsForTraining)
    numDraws = testNetwork(numGames, fnn)
    return numDraws

results = []
initialconfigs = np.array([[9,4,17,0,9], [9,10,5,0,9],[9,16,7,14,9],[9,4,30,20,9], [9,6,0,20,9], [9,20,5,40,9], [9,5,7,2,9], [9,3,0,3,9], [9,5,0,0,9], [9,20,5,20,9]])
p = Pool(multiprocessing.cpu_count())
for i in range(10):
    initialconfigs = createSimilarConfigurations(initialconfigs, 20)
    print "Starting configuration: ", initialconfigs
    tasks = []
    for config in initialconfigs:
        tasks.append((config, inputargs, numGamesTraining, numEpochs, 100))

    print "The computer has this many cores: ", multiprocessing.cpu_count()
    #p = Pool(multiprocessing.cpu_count())

    res = [p.apply_async( trainAndTest, t ) for t in tasks]
    draws = np.array([r.get() for r in res])
    print "Results are", draws
    print "Average is",  float(sum(draws))/len(draws)
    initialconfigs = initialconfigs[draws.argsort()[-15:]]
#print res

#p.map(trainNetwork, )
#print createSimilarConfigurations([[9,10,5,9],[9,16,14,9],[9,3,9]], 10)
#for config in initialconfigs:
#    fnn = trainNetwork(config, inputargs, numGamesTraining, numEpochs)
#    numDraws = testNetwork(100, fnn)
#    results.append(numDraws)
#print results



