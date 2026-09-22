import numpy as np
import scipy.stats as stats

class FastTennisMath:
    def __init__(self, best_of=5, adv_final_set=False):
        self.best_of = best_of
        self.sets_to_win = (best_of // 2) + 1
        
    def game_prob(self, pA, pB, ptA, ptB, is_A_serve):
        p = pA if is_A_serve else (1 - pB)
        dp = np.zeros((5, 5))
        dp[4, 0:3] = 1.0
        dp[3, 3] = p**2 / (p**2 + (1-p)**2)
        
        x, y = min(ptA, 3), min(ptB, 3)
        if ptA >= 3 and ptB >= 3:
            if ptA > ptB: return 1.0
            if ptB > ptA: return 0.0
            x, y = 3, 3
            
        for i in range(3, -1, -1):
            for j in range(3, -1, -1):
                if i==3 and j==3: continue
                dp[i,j] = p * dp[i+1, j] + (1-p) * dp[i, j+1]
        return dp[x, y]

    def tb_prob(self, pA, pB, ptA, ptB, is_A_serve_first):
        dp = np.zeros((8, 8))
        dp[7, 0:6] = 1.0
        dp[6,6] = (pA * (1 - pB)) / (pA * (1 - pB) + (1 - pA) * pB)
        
        x, y = min(ptA, 6), min(ptB, 6)
        if ptA >= 6 and ptB >= 6:
            if ptA > ptB: return 1.0
            if ptB > ptA: return 0.0
            x, y = 6, 6

        for i in range(6, -1, -1):
            for j in range(6, -1, -1):
                if i==6 and j==6: continue
                tot = i + j
                is_first_turn = (tot % 4 == 0) or (tot % 4 == 3)
                is_A_turn = is_A_serve_first if is_first_turn else not is_A_serve_first
                
                p = pA if is_A_turn else (1 - pB)
                dp[i,j] = p * dp[i+1, j] + (1-p) * dp[i, j+1]
        return dp[x, y]

    def set_prob(self, pA, pB, gA, gB, is_A_serve):
        # dp[i, j, s] where s=1 if A serves, s=0 if B serves
        dp_A_wins = np.zeros((8, 8, 2))
        dp_A_next = np.zeros((8, 8, 2)) # Prob A serves next set GIVEN A wins set
        dp_B_next = np.zeros((8, 8, 2)) # Prob A serves next set GIVEN B wins set
        
        # Precompute base probabilities
        gA_win = self.game_prob(pA, pB, 0, 0, True)
        gB_win = self.game_prob(pA, pB, 0, 0, False)
        
        for s in [0, 1]:
            for i in range(8):
                for j in range(8):
                    tot = i + j
                    next_srv = s # if total games is even, same server starts next set
                    
                    if i == 6 and j <= 4:
                        dp_A_wins[i,j,s] = 1.0
                        dp_A_next[i,j,s] = 1.0 if next_srv == 1 else 0.0
                    elif j == 6 and i <= 4:
                        dp_A_wins[i,j,s] = 0.0
                        dp_B_next[i,j,s] = 1.0 if next_srv == 1 else 0.0
                    elif i == 7 and j == 5:
                        dp_A_wins[i,j,s] = 1.0
                        dp_A_next[i,j,s] = 1.0 if next_srv == 1 else 0.0
                    elif j == 7 and i == 5:
                        dp_A_wins[i,j,s] = 0.0
                        dp_B_next[i,j,s] = 1.0 if next_srv == 1 else 0.0

            # TB at 6-6
            # TB server is whoever's turn it is (s)
            p_tb = self.tb_prob(pA, pB, 0, 0, s==1)
            dp_A_wins[6,6,s] = p_tb
            # After TB (13 games), next server is 1-s
            dp_A_next[6,6,s] = 1.0 if (1-s) == 1 else 0.0
            dp_B_next[6,6,s] = 1.0 if (1-s) == 1 else 0.0
            
        for i in range(6, -1, -1):
            for j in range(6, -1, -1):
                if (i==6 and j<=4) or (j==6 and i<=4): continue
                if i==6 and j==6: continue
                
                for s in [0, 1]:
                    p_win = gA_win if s==1 else gB_win
                    
                    dp_A_wins[i,j,s] = p_win * dp_A_wins[i+1, j, 1-s] + (1-p_win) * dp_A_wins[i, j+1, 1-s]
                    
                    # Expected next server is weighted by the outcome
                    if dp_A_wins[i,j,s] > 0:
                        dp_A_next[i,j,s] = (p_win * dp_A_wins[i+1, j, 1-s] * dp_A_next[i+1, j, 1-s] + 
                                          (1-p_win) * dp_A_wins[i, j+1, 1-s] * dp_A_next[i, j+1, 1-s]) / dp_A_wins[i,j,s]
                                          
                    if dp_A_wins[i,j,s] < 1:
                        dp_B_next[i,j,s] = (p_win * (1-dp_A_wins[i+1, j, 1-s]) * dp_B_next[i+1, j, 1-s] + 
                                          (1-p_win) * (1-dp_A_wins[i, j+1, 1-s]) * dp_B_next[i, j+1, 1-s]) / (1 - dp_A_wins[i,j,s])
                                          
        return dp_A_wins[gA, gB, 1 if is_A_serve else 0], dp_A_next[gA, gB, 1 if is_A_serve else 0], dp_B_next[gA, gB, 1 if is_A_serve else 0]

    def match_prob(self, pA, pB, sA, sB, gA, gB, ptA, ptB, is_A_serve):
        if sA == self.sets_to_win: return 1.0
        if sB == self.sets_to_win: return 0.0
        
        # 1. Resolve current game/tb
        is_tb = (gA == 6 and gB == 6)
        if is_tb:
            p_game = self.tb_prob(pA, pB, ptA, ptB, is_A_serve)
        else:
            p_game = self.game_prob(pA, pB, ptA, ptB, is_A_serve)
            
        # 2. Resolve current set from the OUTCOME of this game
        if is_tb:
            # If A wins TB, A wins set.
            p_set = p_game
            p_A_next = 1.0 if not is_A_serve else 0.0 # simplified next server
            p_B_next = 1.0 if not is_A_serve else 0.0
        else:
            # If A wins game -> (gA+1, gB). If B wins -> (gA, gB+1)
            p_set_win_A, a_next_A, b_next_A = self.set_prob(pA, pB, gA+1, gB, not is_A_serve)
            p_set_win_B, a_next_B, b_next_B = self.set_prob(pA, pB, gA, gB+1, not is_A_serve)
            
            p_set = p_game * p_set_win_A + (1-p_game) * p_set_win_B
            if p_set > 0:
                p_A_next = (p_game * p_set_win_A * a_next_A + (1-p_game) * p_set_win_B * a_next_B) / p_set
            else: p_A_next = 0.5
            
            if p_set < 1:
                p_B_next = (p_game * (1-p_set_win_A) * b_next_A + (1-p_game) * (1-p_set_win_B) * b_next_B) / (1-p_set)
            else: p_B_next = 0.5

        # 3. Resolve match
        dp = np.zeros((4, 4, 2))
        for i in range(4):
            for j in range(4):
                if i == self.sets_to_win: dp[i,j,:] = 1.0
                if j == self.sets_to_win: dp[i,j,:] = 0.0
                
        # Precompute full set probs from 0-0
        s_win_A, nA_A, nB_A = self.set_prob(pA, pB, 0, 0, True)
        s_win_B, nA_B, nB_B = self.set_prob(pA, pB, 0, 0, False)
        
        for i in range(self.sets_to_win-1, -1, -1):
            for j in range(self.sets_to_win-1, -1, -1):
                if i == sA and j == sB: continue # handled uniquely
                
                # if A serves
                dp[i,j,1] = s_win_A * (nA_A * dp[i+1, j, 1] + (1-nA_A) * dp[i+1, j, 0]) + \
                            (1-s_win_A) * (nB_A * dp[i, j+1, 1] + (1-nB_A) * dp[i, j+1, 0])
                # if B serves
                dp[i,j,0] = s_win_B * (nA_B * dp[i+1, j, 1] + (1-nA_B) * dp[i+1, j, 0]) + \
                            (1-s_win_B) * (nB_B * dp[i, j+1, 1] + (1-nB_B) * dp[i, j+1, 0])
                            
        # Finally, transition from the current set to the rest of the match
        ans = p_set * (p_A_next * dp[sA+1, sB, 1] + (1-p_A_next) * dp[sA+1, sB, 0]) + \
              (1-p_set) * (p_B_next * dp[sA, sB+1, 1] + (1-p_B_next) * dp[sA, sB+1, 0])
              
        return ans

class BayesianUpdater:
    def __init__(self, pA_initial, pB_initial, prior_weight=100):
        self.prior_weight = prior_weight
        self.pA_prior_wins = pA_initial * prior_weight
        self.pB_prior_wins = pB_initial * prior_weight
        
        self.A_serves = 0
        self.A_wins = 0
        self.B_serves = 0
        self.B_wins = 0
        
    def update(self, is_A_serve, server_won):
        if is_A_serve:
            self.A_serves += 1
            if server_won: self.A_wins += 1
        else:
            self.B_serves += 1
            if server_won: self.B_wins += 1
            
    def get_probs(self):
        pA = (self.pA_prior_wins + self.A_wins) / (self.prior_weight + self.A_serves)
        pB = (self.pB_prior_wins + self.B_wins) / (self.prior_weight + self.B_serves)
        return pA, pB

if __name__ == "__main__":
    math_engine = FastTennisMath(best_of=5)
    print("Testing 0-0:", math_engine.match_prob(0.65, 0.65, 0, 0, 0, 0, 0, 0, True))
    print("Testing A up a break:", math_engine.match_prob(0.65, 0.65, 0, 0, 2, 0, 0, 0, True))
