import random

class SimpleAgent:
    def __init__(self, env, player, opp):
        self.env = env
        self.player = player
        self.opp = opp
        
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
        for x in range(self.env.width):
            if self.isDanger(state, x):
                return x
            
        while True:
            action = random.randint(0, self.env.width-1)
            if state[0, action] == -1:
                return action
        
