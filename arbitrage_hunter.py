import random
import time
from tennis_math import FastTennisMath

class ArbitrageHunter:
    def __init__(self, target_odds=3.0, num_sims=2000):
        """
        target_odds: The odds we want BOTH players to cross during the match.
                     e.g. 3.0 means we want Player A's win probability to drop below 33.3% 
                     AND Player B's win probability to drop below 33.3% at different times.
        """
        self.target_odds = target_odds
        self.lower_prob = 1.0 / target_odds
        self.upper_prob = 1.0 - (1.0 / target_odds)
        self.num_sims = num_sims
        self.math = FastTennisMath(best_of=3)

    def sim_match(self, pA, pB):
        setsA = setsB = gamesA = gamesB = pointsA = pointsB = 0
        servingA = True
        
        min_prob = 1.0
        max_prob = 0.0
        
        while setsA < 2 and setsB < 2:
            is_tiebreak = (gamesA == 6 and gamesB == 6)
            
            # Calculate current live probability from this exact score
            live_prob = self.math.match_prob(pA, pB, setsA, setsB, gamesA, gamesB, pointsA, pointsB, servingA)
            
            if live_prob < min_prob: min_prob = live_prob
            if live_prob > max_prob: max_prob = live_prob
            
            # Early exit: If we already crossed both thresholds, this match is a successful arbitrage!
            if min_prob <= self.lower_prob and max_prob >= self.upper_prob:
                return True
                
            # Play a point
            current_server_prob = pA if servingA else pB
            server_wins = (random.random() < current_server_prob)
            
            if servingA:
                if server_wins: pointsA += 1
                else: pointsB += 1
            else:
                if server_wins: pointsB += 1
                else: pointsA += 1

            # Determine if game/tiebreak is over
            game_over = False
            if is_tiebreak:
                # Tiebreak logic: first to 7, win by 2
                if pointsA >= 7 and pointsA - pointsB >= 2:
                    gamesA += 1
                    game_over = True
                elif pointsB >= 7 and pointsB - pointsA >= 2:
                    gamesB += 1
                    game_over = True
                else:
                    # Tiebreak serve rotation: A, B, B, A, A, B, B...
                    total_pts = pointsA + pointsB
                    if total_pts % 2 == 1:
                        servingA = not servingA
            else:
                # Standard game logic
                if pointsA >= 4 and pointsA - pointsB >= 2:
                    gamesA += 1
                    game_over = True
                elif pointsB >= 4 and pointsB - pointsA >= 2:
                    gamesB += 1
                    game_over = True
                else:
                    # Cap points at 3,3 (Deuce) or 4,3 (Ad) to match FastTennisMath state space
                    if pointsA >= 3 and pointsB >= 3:
                        if pointsA == pointsB: pointsA, pointsB = 3, 3
                        elif pointsA > pointsB: pointsA, pointsB = 4, 3
                        else: pointsA, pointsB = 3, 4

            if game_over:
                pointsA = pointsB = 0
                
                # Check Set winner
                if (gamesA >= 6 and gamesA - gamesB >= 2) or gamesA == 7:
                    setsA += 1
                    gamesA = gamesB = 0
                elif (gamesB >= 6 and gamesB - gamesA >= 2) or gamesB == 7:
                    setsB += 1
                    gamesA = gamesB = 0
                    
                # Standard serve alternates after every game (unless moving to next set after tiebreak)
                # (Simplified serve rotation for simulator speed)
                servingA = not servingA 

        return False # Match finished without double-swing

    def calculate_arbitrage_probability(self, pA, pB):
        success = 0
        for _ in range(self.num_sims):
            if self.sim_match(pA, pB):
                success += 1
        return success / self.num_sims

def main():
    print("===============================================================")
    print(" ARBITRAGE HUNTER: MONTE CARLO VOLATILITY SIMULATOR ")
    print("===============================================================")
    print("Simulating 200 matches per scenario to find Back-To-Lay Swings...")
    
    hunter = ArbitrageHunter(target_odds=3.0, num_sims=200)
    
    scenarios = [
        {"name": "1. ATP Servebots (e.g. Isner vs Karlovic)", "pA": 0.75, "pB": 0.75},
        {"name": "2. ATP Average (e.g. Alcaraz vs Sinner)", "pA": 0.64, "pB": 0.64},
        {"name": "3. WTA Clay / Weak Serves (e.g. Errani vs Paolini)", "pA": 0.54, "pB": 0.54},
        {"name": "4. Heavy Favorite (e.g. Djokovic vs Qualifier)", "pA": 0.75, "pB": 0.55},
    ]
    
    for s in scenarios:
        print(f"\nAnalyzing Scenario: {s['name']}")
        print(f"Serve Win Probabilities: Player A = {s['pA']*100:.1f}%, Player B = {s['pB']*100:.1f}%")
        
        start_time = time.time()
        asp = hunter.calculate_arbitrage_probability(s['pA'], s['pB'])
        duration = time.time() - start_time
        
        print(f"-> Arbitrage Swing Probability (ASP): {asp*100:.1f}%")
        print(f"(Calculated in {duration:.2f} seconds)")
        
        if asp > 0.4:
            print("[RATING: PRIME ARBITRAGE TARGET] Highly volatile match.")
        elif asp > 0.15:
            print("[RATING: AVERAGE] Moderate swings expected.")
        else:
            print("[RATING: TERRIBLE] Do not attempt to trade this match.")

if __name__ == "__main__":
    main()
