import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime
from tennis_math import FastTennisMath, BayesianUpdater

# ==============================================================================
# GITHUB ACTIONS 24/7 TENNIS TRADING BOT
# Runs every 5 minutes.
# ==============================================================================

# Load credentials from environment variables securely
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not configured. Skipping alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

STATE_FILE = "state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except:
            pass
    return set()

def save_state(notified):
    with open(STATE_FILE, "w") as f:
        json.dump(list(notified), f)

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_live_matches():
    url = "https://www.flashscore.mobi/tennis/"
    matches = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for a in soup.find_all('a'):
            href = a.get('href', '')
            if '/match/' in href and '?event=back' not in href:
                match_id = href.split('/')[-2]
                if not any(m['id'] == match_id for m in matches):
                    matches.append({"id": match_id, "url": f"https://www.flashscore.mobi{href}"})
        return matches
    except:
        return []

def get_live_match_details(match_url):
    try:
        response = requests.get(match_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        score_tags = soup.find_all('h4')
        sets_played = [h4.get_text() for h4 in score_tags if "Set" in h4.get_text()]
        
        odds_p = soup.find('p', class_='odds-detail')
        if not odds_p: return None
            
        odds_links = odds_p.find_all('a')
        if len(odds_links) >= 2:
            return {
                "score_text": " | ".join(sets_played) if sets_played else "0-0",
                "home_odds": float(odds_links[0].get_text(strip=True)),
                "away_odds": float(odds_links[1].get_text(strip=True))
            }
    except:
        pass
    return None

from sheets_exporter import export_prediction_to_sheet

def main():
    print(f"[{datetime.now()}] Waking up via GitHub Actions to scan market for 3.0 Arbitrage...")
    math_engine = FastTennisMath(best_of=3)
    updater = BayesianUpdater(pA_initial=0.65, pB_initial=0.65, prior_weight=100)
    
    notified_states = load_state()
    live_matches = get_live_matches()
    print(f"Found {len(live_matches)} matches.")
    
    TARGET_ODDS = 3.0
    
    # Limit to top 15 matches to keep execution under 20 seconds
    for match in live_matches[:15]:
        details = get_live_match_details(match['url'])
        if not details: continue
        
        home_odds, away_odds, score, match_id = details['home_odds'], details['away_odds'], details['score_text'], match['id']
        matchup = f"Match {match_id}"
        
        # Calculate true odds just for reference
        pA_live, pB_live = updater.get_probs()
        our_win_prob = math_engine.match_prob(pA_live, pB_live, 0, 0, 0, 0, 0, 0, True)
        true_home_odds = 1.0 / our_win_prob if our_win_prob > 0 else 999
        true_away_odds = 1.0 / (1 - our_win_prob) if our_win_prob < 1 else 999
        
        # Keys to track if a player has hit 3.0 in this specific match
        p1_key = f"{match_id}_P1_3.0"
        p2_key = f"{match_id}_P2_3.0"
        
        # Check Player 1 (Home)
        if home_odds >= TARGET_ODDS and p1_key not in notified_states:
            notified_states.add(p1_key)
            
            if p2_key in notified_states:
                # Player 2 ALREADY hit 3.0 earlier in the match! This is the perfect Arbitrage completion!
                msg = (
                    f"✅ <b>ARBITRAGE COMPLETED! (DOUBLE SWING)</b> ✅\n\n"
                    f"<b>Match ID:</b> {match_id}\n"
                    f"<b>Score:</b> {score}\n\n"
                    f"Player 2 hit {TARGET_ODDS} earlier, and now Player 1 hit {home_odds}!\n"
                    f"Place your second bet on Player 1 to <b>GREEN OUT for guaranteed profit!</b>\n\n"
                    f"<a href='{match['url']}'>View Match</a>"
                )
            else:
                # First leg of the arbitrage
                msg = (
                    f"🚨 <b>ARBITRAGE LEG 1 OPENED</b> 🚨\n\n"
                    f"<b>Match ID:</b> {match_id}\n"
                    f"<b>Score:</b> {score}\n\n"
                    f"Player 1 just crossed {TARGET_ODDS} (Current: {home_odds}).\n"
                    f"Place your first bet on Player 1 and wait for the match to swing!\n\n"
                    f"<a href='{match['url']}'>View Match</a>"
                )
                
            print(f"ARB ALERT: P1 crossed {TARGET_ODDS} in {match_id}")
            send_telegram_alert(msg)
            
            date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            export_prediction_to_sheet(date_str, match_id, matchup, score, "Player 1", home_odds, true_home_odds, 0)
            
        # Check Player 2 (Away)
        if away_odds >= TARGET_ODDS and p2_key not in notified_states:
            notified_states.add(p2_key)
            
            if p1_key in notified_states:
                # Player 1 ALREADY hit 3.0 earlier!
                msg = (
                    f"✅ <b>ARBITRAGE COMPLETED! (DOUBLE SWING)</b> ✅\n\n"
                    f"<b>Match ID:</b> {match_id}\n"
                    f"<b>Score:</b> {score}\n\n"
                    f"Player 1 hit {TARGET_ODDS} earlier, and now Player 2 hit {away_odds}!\n"
                    f"Place your second bet on Player 2 to <b>GREEN OUT for guaranteed profit!</b>\n\n"
                    f"<a href='{match['url']}'>View Match</a>"
                )
            else:
                # First leg of the arbitrage
                msg = (
                    f"🚨 <b>ARBITRAGE LEG 1 OPENED</b> 🚨\n\n"
                    f"<b>Match ID:</b> {match_id}\n"
                    f"<b>Score:</b> {score}\n\n"
                    f"Player 2 just crossed {TARGET_ODDS} (Current: {away_odds}).\n"
                    f"Place your first bet on Player 2 and wait for the match to swing!\n\n"
                    f"<a href='{match['url']}'>View Match</a>"
                )
                
            print(f"ARB ALERT: P2 crossed {TARGET_ODDS} in {match_id}")
            send_telegram_alert(msg)
            
            date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            export_prediction_to_sheet(date_str, match_id, matchup, score, "Player 2", away_odds, true_away_odds, 0)
        
        time.sleep(1)
        
    save_state(notified_states)
    print("Arbitrage scan complete. Shutting down until next cron run.")

if __name__ == "__main__":
    main()
