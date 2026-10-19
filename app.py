import streamlit as st
import time
import numpy as np
import pandas as pd
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashplayerstats

st.set_page_config(page_title="NBA Projection Engine", page_icon="🏀", layout="wide")

st.title("🏀 NBA Projection Engine")
st.caption("Live Monte Carlo projections • Built for mobile")

@st.cache_data(ttl=300)
def get_todays_games():
    board = scoreboard.ScoreBoard()
    games = board.games.get_dict()
    result = []
    for g in games:
        result.append({
            "home": g["homeTeam"]["teamTricode"],
            "away": g["awayTeam"]["teamTricode"],
        })
    return result

@st.cache_data(ttl=600)
def get_team_stats(season="2025-26"):
    time.sleep(0.6)
    stats = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame"
    )
    df = stats.get_data_frames()[0]
    return df[["TEAM_ABBREVIATION", "PACE", "OFF_RATING", "DEF_RATING"]].set_index("TEAM_ABBREVIATION")

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

def run_simulation(home_ortg, away_ortg, pace, n_sims=5000):
    home_scores = []
    away_scores = []
    for _ in range(n_sims):
        p = max(90, int(np.random.normal(pace, 3)))
        h = sum(simulate_possession(home_ortg) for _ in range(p))
        a = sum(simulate_possession(away_ortg) for _ in range(p))
        home_scores.append(max(75, h + np.random.normal(0, 2.5)))
        away_scores.append(max(75, a + np.random.normal(0, 2.5)))
    
    home_scores = np.array(home_scores)
    away_scores = np.array(away_scores)
    
    return {
        "home_mean": home_scores.mean(),
        "away_mean": away_scores.mean(),
        "total": (home_scores + away_scores).mean(),
        "home_win": (home_scores > away_scores).mean()
    }

# Main UI
if st.button("🔄 Run Live Projections", use_container_width=True):
    with st.spinner("Pulling live NBA data and running simulations..."):
        try:
            games = get_todays_games()
            team_stats = get_team_stats()
            
            if not games:
                st.warning("No games found today.")
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
                    
                    st.subheader(f"{away} @ {home}")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Away Score", f"{sim['away_mean']:.1f}")
                    col2.metric("Home Score", f"{sim['home_mean']:.1f}")
                    col3.metric("Total", f"{sim['total']:.1f}")
                    
                    st.write(f"**Home Win Probability:** {sim['home_win']:.1%}")
                    st.divider()
                    
        except Exception as e:
            st.error(f"Error: {e}")
            st.info("The NBA API sometimes has temporary issues. Try again in 30 seconds.")

st.markdown("---")
st.caption("Data from NBA.com • Monte Carlo simulation • Refreshes when you click the button")
