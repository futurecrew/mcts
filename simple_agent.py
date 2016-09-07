import random

class SimpleAgent:
    def __init__(self, env, me, opp):
        self.env = env
        self.me = me
        self.opp = opp
        
    def isWin(self, state, meX):
        newState = state.copy()
        for i in range(self.env.height-1, -1, -1):
            if newState[i, meX] == -1:
                newState[i, meX] = self.me
                gameOver, winner = self.env.checkGameOver(newState)
                if gameOver:
                    return True
                else:
                    return False
        
    def isDanger(self, state, oppX):
        newState = state.copy()
        for i in range(self.env.height-1, -1, -1):
            if newState[i, oppX] == -1:
                newState[i, oppX] = self.opp
                gameOver, winner = self.env.checkGameOver(newState)
                if gameOver:
                    return True
                else:
                    return False
            
    def getAction(self, state):
        availableActions = self.env.availableActions(state)
        
        if len(availableActions) == 1:
            return availableActions[0]

        for x in availableActions:
            if self.isWin(state, x):
                return x
            
        for x in availableActions:
            if self.isDanger(state, x):
                return x
            
        while True:
            i = random.randint(0, len(availableActions)-1)
            return availableActions[i]            
        
