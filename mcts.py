import os
import time
import pickle
import math
import threading
import random
import numpy as np
import util
from connect_four_env import ConnectFourEnv
from simple_agent import SimpleAgent
from matplotlib.style.core import available

class MCTS:
    def __init__(self, settings):
        self.settings = settings
        self.totalGameNo = settings['total_game_no']
        self.playedGameNo = 0
        self.simStepNo = settings['sim_step_no']
        self.display = settings['display']
        self.env = ConnectFourEnv(self.display)
        self.visited = {}           # (stateStr, turn, action), visited
        self.won = {}              # (stateStr, turn, action), won
        self.DRAW = -1
        self.PLAYER = 1
        self.OPP = 2
        self.simpleAgent = SimpleAgent(self.env, self.OPP, self.PLAYER)
        self.winnerResult = {self.DRAW:0, self.PLAYER:0, self.OPP:0}
        self.greedyEpsilon = 0.1

        self.startTime = time.strftime('%Y%m%d_%H%M%S')
        logFile="output/%s.log" % (self.startTime)            
        util.Logger(logFile)

        self.testMode = False
        self.debugger = DebugInput(self).start()

    def printEnv(self):
        print 'Start time: %s' % self.startTime
        print '[ Running Environment ]'
        for key in self.settings.keys():
            print '{} : '.format(key).ljust(30) + '{}'.format(self.settings[key])
        print 'width: %s, height: %s' % (self.env.width, self.env.height)
    
    def getStateStr(self, state):
        #return np.array_str(state)
        return hash(state.tostring())
    
    def simulate(self, orgState):
        state = orgState.copy()
        turn = self.PLAYER
        history = []
        expanded = False

        for i in range(self.simStepNo):
            if turn == self.PLAYER:
                availableActions = self.env.availableActions(state)
                stateStr = self.getStateStr(state)
                totalStateVisited = 0
                # check every actions are visited before
                for action in availableActions:
                    stateActionPair = (stateStr, turn, action)
                    if stateActionPair in self.visited:
                        totalStateVisited += self.visited[stateActionPair]
                    else:
                        totalStateVisited = 0

                if totalStateVisited == 0:
                    action = self.getRandomAction(state)
                else:
                    maxUpperBound = 0            
                    for action in availableActions:
                        stateActionPair = (stateStr, turn, action)
                        won = self.won.get(stateActionPair, 0)
                        visited = max(self.visited.get(stateActionPair, 1), 1)
                        winRatio = float(won) / visited
                        upperBound = winRatio + math.sqrt(2 * math.log(totalStateVisited) / visited)
                        if upperBound >= maxUpperBound:
                            maxUpperBound = upperBound
                            selectedAction = action
                    action = selectedAction
            elif turn == self.OPP:
                if 'sim_opp_policy' in self.settings and self.settings['sim_opp_policy'] == 'simple':
                    action = self.simpleAgent.getAction(state)
                else:
                    action = self.getRandomAction(state)
            
            stateStr = self.getStateStr(state)
            stateActionPair = (stateStr, turn, action)
            if expanded == False and stateActionPair not in self.visited:
                canExpand = True
                expanded = True
            else:
                canExpand = False
                
            state, gameOver, winner = self.doAction(state, action, turn, history, canExpand, False)
                          
            if turn == self.PLAYER:
                turn = self.OPP
            else:
                turn = self.PLAYER

            if gameOver:
                self.updateTreeInfo(winner, history)
                # restart sim
                self.env.reset()
                self.env.setState(orgState)
                state = orgState.copy()                
                turn = self.PLAYER
                history = []
                expanded = False
                continue

        self.env.reset()
        self.env.setState(orgState)       # restore back the environment state

    def getRandomAction(self, state, availableActions=None):
        if availableActions == None:
            availableActions = self.env.availableActions(state)
        actionIndex = random.randint(0, len(availableActions)-1)
        return availableActions[actionIndex]

    def getAction(self, state, turn):
        availableActions = self.env.availableActions(state)
        
        if len(availableActions) == 1:
            return availableActions[0]
        
        maxAction = -1
        maxWinRatio = 0
        availableActions = self.env.availableActions(state)
        stateStr = self.getStateStr(state)
        for action in availableActions:
            stateActionPair = (stateStr, turn, action)
            if stateActionPair not in self.visited:
                continue
            winRatio = float(self.won.get(stateActionPair, 0)) / max(self.visited.get(stateActionPair, 1), 1)
            if winRatio >= maxWinRatio:
                maxWinRatio = winRatio
                maxAction = action

        return maxAction
        
    def getActionEGreedy(self, state, turn):
        if random.random() < self.greedyEpsilon and self.testMode == False:
            return self.getRandomAction(state)
        else:
            maxAction = -1
            maxWinRatio = 0
            availableActions = self.env.availableActions(state)
            stateStr = self.getStateStr(state)
            for action in availableActions:
                stateActionPair = (stateStr, turn, action)
                if stateActionPair not in self.visited:
                    continue
                winRatio = float(self.won.get(stateActionPair, 0)) / max(self.visited.get(stateActionPair, 1), 1)
                if winRatio >= maxWinRatio:
                    maxWinRatio = winRatio
                    maxAction = action

            if maxAction != -1:
                return maxAction
            else:    
                return self.getRandomAction(state)
        
    def doAction(self, state, action, turn, history, canExpand, display):
        newState, gameOver, winner = self.env.act(turn, action, display)
        
        stateStr = self.getStateStr(state)
        stateActionPair = (stateStr, turn, action)
        if stateActionPair not in self.visited and canExpand:
            self.visited[stateActionPair] = 0
            self.won[stateActionPair] = 0
        history.append((stateActionPair, turn))
        return newState, gameOver, winner
        
    def updateTreeInfo(self, winner, history):
        """ Update win result from the current node to the top node """

        for stateActionPair, turn in history:
            if stateActionPair in self.visited:
                self.visited[stateActionPair] += 1
                if turn == winner:
                    self.won[stateActionPair] += 1
    
    def printHistory(self, history):
        step = 0
        print '\n[ history ]'
        for stateActionPair, turn in history:
            state, turn2, action = stateActionPair
            if stateActionPair in self.visited:
                visited = self.visited[stateActionPair]
                won = self.won[stateActionPair]
            else:
                visited = 0
                won = 0
                
            print 'step[%s] turn=%s, action=%s, visited=%s, won=%s' % \
                    (step, turn, action, visited, won)
            step += 1
        print ''
        
    def printResult(self):
        print 'total states: %s' % len(self.visited)
                    
    def save(self, step):
        if os.path.exists('snapshot') == False:
            os.makedirs('snapshot')
        fileName = 'snapshot/mcts_%s' % step
        with open(fileName + '.pickle', 'wb') as f:
            pickle.dump(self, f)
        
    def gogo(self):
        lastResult = []
        lastResultWin = 0
        for i in range(self.totalGameNo):
            self.env.reset()
            state = self.env.getState()
            history = []
            turn = random.randint(self.PLAYER, self.OPP)

            while True:
                if turn == self.PLAYER:
                    self.simulate(state)
                    if settings['player_action'] == 'egreedy':
                        action = self.getActionEGreedy(state, self.PLAYER)
                    else:
                        action = self.getAction(state, self.PLAYER)
                elif turn == self.OPP:
                    if settings['opponent'] == 'user':
                        action = self.env.getManualAction(state)
                    else:
                        action = self.simpleAgent.getAction(state)
                
                state, gameOver, winner = self.doAction(state, action, turn, history, True, True)

                if gameOver:
                    break
                
                if turn == self.PLAYER:
                    turn = self.OPP
                else:
                    turn = self.PLAYER
            
            if settings['opponent'] == 'user':
                self.env.showWinner(winner)
                
            self.playedGameNo += 1
            
            self.winnerResult[winner] += 1
            if winner == -1:
                print 'Game draw'
            else:
                mcts.updateTreeInfo(winner, history)
                if winner == self.PLAYER:
                    lastResultWin += 1
                if len(lastResult) == 100:
                    todel = lastResult.pop(0)
                    if todel == 1:
                        lastResultWin -= 1
                lastResult.append(winner)
                lastRatio = float(lastResultWin) * 100 / len(lastResult)
                #mcts.printResult()
                winRatio = float(self.winnerResult[self.PLAYER]) * 100 \
                                     / (self.winnerResult[self.OPP] + self.winnerResult[self.PLAYER])
                
                if winner == 1:
                    winStr = 'Win'
                else:
                    winStr = 'Lose'
                print 'Game %s : %s, %s, total=%.0f%%, last 100=%.0f%%' % (self.playedGameNo, self.winnerResult, winStr, winRatio, lastRatio)
            
            if i > 0 and i % 5000 == 0:
                self.save(i)
            #time.sleep(5)
    
        self.debugger.finish()
    
class DebugInput(threading.Thread):
    def __init__(self, player):
        threading.Thread.__init__(self)
        self.player = player
        self.running = True
    
    def run(self):
        time.sleep(2)
        while (self.running):
            input = raw_input('')
            if input == 'd':
                if self.player.env.display:
                    self.player.env.closeDisplay()
                else:
                    self.player.env.initDisplay()
                print 'Display : %s' % self.player.env.display
            elif input == 't':
                self.player.testMode = not self.player.testMode
                print 'Test mode : %s' % self.player.testMode
                
    def finish(self):
        self.running = False
    
def load(savedFile):
    with open(savedFile) as f:
        print 'Loading %s' % savedFile
        loaded = pickle.load(f)
        print 'Loading done'
        return loaded
    print 'Error while open %s' % savedFile
        
if __name__ == '__main__':
    settings = {}
    settings['total_game_no'] = 100000
    settings['sim_step_no'] = 1000
    #settings['display'] = True
    settings['display'] = False
    settings['player_action'] = 'mcts'

    #settings['opponent'] = 'user'
    settings['opponent'] = 'simpleAgent'
    
    settings['sim_opp_policy'] = 'simple'
    #settings['sim_opp_policy'] = 'random'
    
    if settings['opponent'] == 'user':
        settings['display'] = True
        
    #mcts = load('snapshot/mcts_5000.pickle')
    mcts = MCTS(settings)
    
    mcts.printEnv()
    mcts.gogo()
        
