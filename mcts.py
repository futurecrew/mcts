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
from multiprocessing import Process, Queue

class MCTS:
    def __init__(self, settings):
        self.settings = settings
        self.totalGameNo = settings['total_game_no']
        self.playedGameNo = 0
        self.simStepNo = settings['sim_step_no']
        self.saveStepNo = settings['save_step_no']
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

    def initializeProcesses(self):
        # Multi process jobs
        self.multiCpuNo = self.settings['multi_cpu_no']
        self.queueList = []
        self.processList = []
        self.queueChild2Parent = Queue()
        for i in range(self.multiCpuNo):        
            queueParent2Child = Queue()
            self.queueList.append(queueParent2Child)
            #print 'creating a child process[%s]' % i
            p = Process(target=self.simulateOne, args=(i, self.simStepNo / self.multiCpuNo, 
                                                       queueParent2Child, self.queueChild2Parent))
            p.start()
            self.processList.append(p)

    def __getstate__(self):
        d = dict(self.__dict__)
        del d['queueList']
        del d['processList']
        del d['queueChild2Parent']
        return d

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
        time1 = time.time()
        for i in range(self.multiCpuNo):
            self.queueList[i].put((orgState, self.visited, self.won))
            
        finishedChildNo = 0
        for i in range(self.multiCpuNo):
            childID, winnerList, historyList, expandedList = self.queueChild2Parent.get()
            
            for expandedNode in expandedList:
                if expandedNode not in self.visited:
                    self.visited[expandedNode] = 0
                    self.won[expandedNode] = 0
            
            for winner, history in zip(winnerList, historyList):
                self.updateTreeInfo(winner, history)
            
            finishedChildNo += 1
            
            #print 'simulateOne done %s' % childID
            if finishedChildNo == self.multiCpuNo:
                break
        #print 'all simulateOne finished'
        time2 = time.time()
        
        #print 'simulte took %.2f sec' % (time2 - time1)
        

    def simulateOne(self, id, simStepNo, queueParent2Child, queueChild2Parent):
        while True:
            orgState, visited, won = queueParent2Child.get()
            self.visited = visited
            self.won = won
            self.env.reset()
            self.env.setState(orgState)
            
            self.visited['haha'] = 'dj'

            historyList = []
            winnerList = []
            expandedList = []
            state = orgState.copy()
            turn = self.PLAYER
            history = []
            expanded = False
    
            for i in range(simStepNo):
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
                    
                state, gameOver, winner = self.doAction(state, action, turn, history, expandedList, canExpand, False)
                              
                if turn == self.PLAYER:
                    turn = self.OPP
                else:
                    turn = self.PLAYER
    
                if gameOver:
                    self.updateTreeInfo(winner, history)
                    historyList.append(history)
                    winnerList.append(winner)
                    
                    # restart sim
                    self.env.reset()
                    self.env.setState(orgState)
                    state = orgState.copy()                
                    turn = self.PLAYER
                    history = []
                    expanded = False
                    continue
    
            queueChild2Parent.put((id, winnerList, historyList, expandedList))

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
        
    def doAction(self, state, action, turn, history, expandedList, canExpand, display):
        newState, gameOver, winner = self.env.act(turn, action, display)
        
        stateStr = self.getStateStr(state)
        stateActionPair = (stateStr, turn, action)
        if stateActionPair not in self.visited and canExpand:
            self.visited[stateActionPair] = 0
            self.won[stateActionPair] = 0
            if expandedList != None:
                expandedList.append(stateActionPair)
        history.append(stateActionPair)
        return newState, gameOver, winner
        
    def updateTreeInfo(self, winner, history):
        """ Update win result from the current node to the top node """

        for stateActionPair in history:
            if stateActionPair in self.visited:
                self.visited[stateActionPair] += 1
                _, turn, _ = stateActionPair
                if turn == winner:
                    self.won[stateActionPair] += 1
    
    def printHistory(self, history):
        step = 0
        print '\n[ history ]'
        for stateActionPair in history:
            state, turn, action = stateActionPair
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
        self.initializeProcesses()

        lastResult = []
        lastResultWin = 0
        for i in range(self.totalGameNo):
            self.env.reset()
            state = self.env.getState()
            history = []
            turn = random.randint(self.PLAYER, self.OPP)
            startTime = time.time()
            
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
                
                state, gameOver, winner = self.doAction(state, action, turn, history, None, True, True)

                if gameOver:
                    break
                
                if turn == self.PLAYER:
                    turn = self.OPP
                else:
                    turn = self.PLAYER

            elapsed = time.time() - startTime
            
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
                print 'Game %s : %s, %s, total=%.0f%%, last 100=%.0f%%, %.1fs' % (self.playedGameNo, self.winnerResult, winStr, winRatio, lastRatio, elapsed)
            
            if self.playedGameNo % self.saveStepNo == 0:
                self.save(self.playedGameNo)
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
    
def load(savedFile, settings):
    with open(savedFile) as f:
        print 'Loading %s' % savedFile
        loaded = pickle.load(f)
        loaded.env.display = settings['display']
        if loaded.env.display == True:
            loaded.env.initDisplay()
        loaded.settings['opponent'] = settings['opponent']
        loaded.settings['sim_opp_policy'] = settings['sim_opp_policy']
        print 'Loading done'
        return loaded
    print 'Error while open %s' % savedFile
        
if __name__ == '__main__':
    settings = {}
    settings['total_game_no'] = 100000
    settings['sim_step_no'] = 10000
    settings['save_step_no'] = 100
    #settings['display'] = True
    settings['display'] = False
    settings['player_action'] = 'mcts'
    settings['multi_cpu_no'] = 7

    settings['opponent'] = 'user'
    #settings['opponent'] = 'simpleAgent'
    
    settings['sim_opp_policy'] = 'simple'
    #settings['sim_opp_policy'] = 'random'
    
    if settings['opponent'] == 'user':
        settings['display'] = True
        
    mcts = load('snapshot/mcts_100.pickle', settings)
    #mcts = MCTS(settings)
    
    mcts.printEnv()
    mcts.gogo()
        
