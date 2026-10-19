import streamlit as st
import time
import numpy as np
import pandas as pd
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.library.http import NBAStatsHTTP

# Make the API act more like a real browser
NBAStatsHTTP.headers = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'Connection': 'keep-alive',
}

st.set_page_config(page_title="NBA Projection Engine", page_icon="🏀", layout="wide")

st.title("🏀 NBA Projection Engine")
st.caption("Live Monte Carlo projections • Mobile friendly")

def get_todays_games():
    try:
        board = scoreboard.ScoreBoard()
        games = board.games.get_dict()
        result = []
        for g in games:
            result.append({
                "home": g["homeTeam"]["teamTricode"],
                "away": g["awayTeam"]["teamTricode"],
            })
        return result
    except Exception as e:
        return []

def get_team_stats(season="2025-26"):
    try:
        time.sleep(1.5)
        stats = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            timeout=60
        )
        df = stats.get_data_frames()[0]
        return df[["TEAM_ABBREVIATION", "PACE", "OFF_RATING", "DEF_RATING"]].set_index("TEAM_ABBREVIATION")
    except Exception as e:
        return pd.DataFrame()

def simulate_possession(ortg):
    base = ortg / 100
    if np.random.random() < 0.13:
        return 0
    if np.random.random() < 0.39:
        if np.random.random() < min(0.40, 0.34 * base / 1.12):
            return 3
        if np.random.random() < 0.27:
            return simulate_possession(ortg * 0.93)
        return 0
    else:
        if np.random.random() < 0.17:
            return np.random.choice([1, 2], p=[0.28, 0.72])
        if np.random.random() < min(0.55, 0.50 * base / 1.12):
            return 2
        if np.random.random() < 0.27:
            return simulate_possession(ortg * 0.93)
        return 0

def run_simulation(home_ortg, away_ortg, pace, n_sims=2500):
    home_scores = np.zeros(n_sims)
    away_scores = np.zeros(n_sims)
    for i in range(n_sims):
        p = max(90, int(np.random.normal(pace, 3)))
        h = sum(simulate_possession(home_ortg) for _ in range(p))
        a = sum(simulate_possession(away_ortg) for _ in range(p))
        home_scores[i] = max(75, h + np.random.normal(0, 2.5))
        away_scores[i] = max(75, a + np.random.normal(0, 2.5))
    
    return {
        "home_mean": round(float(home_scores.mean()), 1),
        "away_mean": round(float(away_scores.mean()), 1),
        "total": round(float((home_scores + away_scores).mean()), 1),
        "home_win": round(float((home_scores > away_scores).mean() * 100), 1)
    }

st.markdown("### Click the button below to run live projections")

if st.button("🔄 Run Live Projections", use_container_width=True, type="primary"):
    with st.spinner("Trying to pull live NBA data... (this can take up to 60 seconds)"):
        games = get_todays_games()
        team_stats = get_team_stats()
        
        if team_stats.empty or len(games) == 0:
            st.error("NBA API is currently blocking or timing out from this server.")
            st.info("This is a known issue with free cloud hosts. The API works better from a normal home connection.")
            st.write("Possible solutions:")
            st.write("1. Try again in a few minutes")
            st.write("2. Use a different host later (Railway, a VPS, etc.)")
        else:
            for g in games:
                home = g["home"]
                away = g["away"]
                
                if home not in team_stats.index or away not in team_stats.index:
                    continue
                
                h = team_stats.loc[home]
                a = team_stats.loc[away]
                pace = (h["PACE"] + a["PACE"]) / 2
                
                sim = run_simulation(h["OFF_RATING"] + 2.5, a["OFF_RATING"], pace)
                
                st.subheader(f"{away}  @  {home}")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Away", f"{sim['away_mean']}")
                c2.metric("Home", f"{sim['home_mean']}")
                c3.metric("Total", f"{sim['total']}")
                c4.metric("Home Win %", f"{sim['home_win']}%")
                
                st.divider()

st.markdown("---")
st.caption("Data via NBA.com • Monte Carlo simulation")
