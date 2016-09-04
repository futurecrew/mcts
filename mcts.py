import time
import math
import random
import numpy as np
from connect_four_env import ConnectFourEnv
from simple_agent import SimpleAgent
from matplotlib.style.core import available

class MCTS:
    def __init__(self, totalGameNo, simStepNo, display):
        self.totalGameNo = totalGameNo
        self.simStepNo = simStepNo
        self.display = display
        self.env = ConnectFourEnv(display)
        self.child = {}              # (stateStr, turn, action), childStateStr
        self.parent = {}           # (stateStr, turn, action), parentStateStr 
        self.visited = {}           # (stateStr, turn, action), visited
        self.won = {}              # (stateStr, turn, action), won
        self.DRAW = -1
        self.PLAYER = 1
        self.OPP = 2
        self.simpleAgent = SimpleAgent(self.env, self.PLAYER, self.OPP)
        self.winnerResult = {self.DRAW:0, self.PLAYER:0, self.OPP:0}
        self.greedyEpsilon = 0.1
    
    def getStateStr(self, state):
        return np.array_str(state)
    
    def simulate(self, orgState):
        state = orgState.copy()
        turn = self.PLAYER
        history = []

        for i in range(self.simStepNo):
            if turn == self.PLAYER:
                action = self.getAction(state, self.PLAYER, 'simulate')
            elif turn == self.OPP:
                #action = self.simpleAgent.getAction(state)
                action = self.getRandomAction(state)
            
            state, gameOver, winner = self.doAction(state, action, turn, history)
                          
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
                continue

        self.env.reset()
        self.env.setState(orgState)       # restore back the environment state

    def getRandomAction(self, state, availableActions=None):
        if availableActions == None:
            availableActions = self.env.availableActions(state)
        actionIndex = random.randint(0, len(availableActions)-1)
        return availableActions[actionIndex]

    def getAction(self, state, turn, fromF):
        stateStr = self.getStateStr(state)
        availableActions = self.env.availableActions(state)
        totalStateVisited = 0
        
        self.simulate(state)
        
        # check every actions are visited before
        for action in availableActions:
            stateActionPair = (stateStr, turn, action)
            if stateActionPair in self.visited and self.visited[stateActionPair] > 0:
                totalStateVisited += self.visited[stateActionPair]
            else:
                totalStateVisited = 0
                break

        if totalStateVisited > 0:
            maxUpperBound = 0            
            if fromF =='gogo':
                pass
            for action in availableActions:
                stateActionPair = (stateStr, turn, action)
                winRatio = float(self.won[stateActionPair]) / self.visited[stateActionPair]
                upperBound = winRatio + math.sqrt(2 * math.log(totalStateVisited) / self.visited[stateActionPair])
                if upperBound >= maxUpperBound:
                    maxUpperBound = upperBound
                    selectedAction = action
            return selectedAction
        else:
            return self.getRandomAction(state, availableActions)
        """
        if random.random() < self.greedyEpsilon:
            #print 'getAction return2'
            return self.getRandomAction(availableActions)
        else:
            maxAction = 0
            maxWinRatio = 0
            for action, childStateStr in zip(self.childAction[stateStr], self.children[stateStr]):
                winRatio = float(self.won[childStateStr]) / self.visited[childStateStr]
                if winRatio > maxWinRatio:
                    maxWinRatio = winRatio
                    maxAction = action
            #print 'getAction return3'
            return maxAction
        """
        
    def doAction(self, state, action, turn, history):
        newState, gameOver, winner = self.env.act(turn, action)
        
        stateStr = self.getStateStr(state)
        newStateStr = self.getStateStr(newState)
        stateActionPair = (stateStr, turn, action)
        newStateActionPair = (newStateStr, turn, action)
        self.child[stateActionPair] = newStateStr
        self.parent[newStateActionPair] = stateStr
        history.append((stateActionPair, turn))
        return newState, gameOver, winner
        
    def updateTreeInfo(self, winner, history):
        """ Update win result from the current node to the top node """
        
        print 'history before. winner=%s' % winner
        self.printHistory(history)
        
        for stateActionPair, turn in history:
            if stateActionPair not in self.visited:
                self.visited[stateActionPair] = 0
                self.won[stateActionPair] = 0
            self.visited[stateActionPair] += 1
            if turn == winner:
                self.won[stateActionPair] += 1

        print 'history after'
        self.printHistory(history)
    
    def printHistory(self, history):
        step = 0
        print '\n[ history ]'
        for stateActionPair, turn in history:
            stateStr, turn2, action = stateActionPair
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
                    
    def gogo(self):
        for i in range(self.totalGameNo):
            self.env.reset()
            state = self.env.getState()
            history = []
            while True:
                action = self.simpleAgent.getAction(state)
                #print 'action1: %s' % action
                state, gameOver, winner = self.doAction(state, action, self.OPP, history)
                #time.sleep(0.5)
                if gameOver:
                    break
                action = self.getAction(state, self.PLAYER, 'gogo')
                #print 'action2: %s' % action
                state, gameOver, winner = self.doAction(state, action, self.PLAYER, history)
                #time.sleep(0.5)
                if gameOver:
                    break
            
            if winner == -1:
                print 'Game draw'
            else:
                mcts.updateTreeInfo(winner, history)
                self.winnerResult[winner] += 1                
                #mcts.printResult()
                print 'Player %s won' % winner
                print 'winnerResult: %s' % self.winnerResult
            #time.sleep(5)
        
if __name__ == '__main__':
    totalGameNo = 1000
    simStepNo = 300
    #display = True
    display = False
    
    mcts = MCTS(totalGameNo, simStepNo, display)
    mcts.gogo()
        
