import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from tennis_math import FastTennisMath, BayesianUpdater

# ==============================================================================
# PRODUCTION 24/7 TENNIS TRADING BOT
# Platform: Render.com (Background Worker)
# Notifications: Telegram Push
# ==============================================================================

# Telegram Credentials
TELEGRAM_TOKEN = "8921406191:AAGyaoeEZbP5ftwWZb7pE3m3qdh94dEL7ik"
TELEGRAM_CHAT_ID = "927792749"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )
}

# Keep track of alerts we've already sent so we don't spam your phone 
# for the same edge on the same scoreline.
notified_edges = set()

def send_telegram_alert(message):
    """Sends a push notification to your Telegram app."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def get_live_matches():
    url = "https://www.flashscore.mobi/tennis/"
    matches = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        match_links = soup.find_all('a')
        for a in match_links:
            href = a.get('href', '')
            if '/match/' in href and '?event=back' not in href:
                match_id = href.split('/')[-2]
                if not any(m['id'] == match_id for m in matches):
                    matches.append({
                        "id": match_id,
                        "url": f"https://www.flashscore.mobi{href}"
                    })
        return matches
    except Exception as e:
        print(f"Error scraping main page: {e}")
        return []

def get_live_match_details(match_url):
    try:
        response = requests.get(match_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        score_tags = soup.find_all('h4')
        sets_played = [h4.get_text() for h4 in score_tags if "Set" in h4.get_text()]
        
        odds_p = soup.find('p', class_='odds-detail')
        if not odds_p:
            return None
            
        odds_links = odds_p.find_all('a')
        if len(odds_links) >= 2:
            return {
                "score_text": " | ".join(sets_played) if sets_played else "0-0",
                "home_odds": float(odds_links[0].get_text(strip=True)),
                "away_odds": float(odds_links[1].get_text(strip=True))
            }
    except Exception:
        pass
    return None

def main_loop():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bot starting up on Render...")
    send_telegram_alert("🚀 <b>Tennis Trading Bot Started!</b>\nRunning 24/7 on Render.com. I will notify you when I find massive edges.")
    
    math_engine = FastTennisMath(best_of=3)
    updater = BayesianUpdater(pA_initial=0.65, pB_initial=0.65, prior_weight=100)
    
    while True:
        try:
            live_matches = get_live_matches()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(live_matches)} live matches...")
            
            for match in live_matches:
                details = get_live_match_details(match['url'])
                if not details:
                    continue
                
                home_odds = details['home_odds']
                away_odds = details['away_odds']
                score = details['score_text']
                match_id = match['id']
                
                # Compute Bayesian True Odds
                pA_live, pB_live = updater.get_probs()
                our_win_prob = math_engine.match_prob(pA_live, pB_live, 0, 0, 0, 0, 0, 0, True)
                
                # Calculate Expected Value on P1
                ev_home = (our_win_prob * (home_odds - 1)) - ((1 - our_win_prob) * 1)
                
                if ev_home > 0.05:
                    alert_id = f"{match_id}_home_{score}_{home_odds}"
                    if alert_id not in notified_edges:
                        notified_edges.add(alert_id)
                        true_odds = 1.0 / our_win_prob
                        
                        msg = (
                            f"🚨 <b>MASSIVE EDGE DETECTED</b> 🚨\n\n"
                            f"<b>Match ID:</b> {match_id}\n"
                            f"<b>Score:</b> {score}\n\n"
                            f"💰 <b>Market Odds:</b> {home_odds:.2f}\n"
                            f"🎯 <b>True Fair Odds:</b> {true_odds:.2f}\n"
                            f"📈 <b>Expected Value:</b> {ev_home*100:.1f}%\n\n"
                            f"<a href='{match['url']}'>View Match</a>"
                        )
                        print(f"EDGE FOUND: {match_id} - EV: {ev_home*100:.1f}%")
                        send_telegram_alert(msg)
                
                time.sleep(1.5) # Gentle polling to avoid rate limits
                
            print("Cycle complete. Sleeping for 60 seconds...")
            time.sleep(60) # Wait 1 minute before checking the site again
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(60) # Sleep on error and retry

if __name__ == "__main__":
    main_loop()
