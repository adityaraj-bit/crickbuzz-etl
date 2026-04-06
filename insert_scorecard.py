from db import get_or_create_player, get_or_create_team
from utils import safe_int, safe_float


def insert_scorecard(conn, match_id, team1_id, team2_id, scorecard_data):
    cur = conn.cursor()

    # We need to ensure ALL 11 players of BOTH teams are in both tables.
    # It's easiest to pre-populate them for both teams first if they aren't there.
    all_teams = {team1_id, team2_id}
    for t_id in all_teams:
        cur.execute("SELECT player_id FROM playing_xi WHERE match_id = ? AND team_id = ?", (match_id, t_id))
        players = [r[0] for r in cur.fetchall()]
        
        for pid in players:
            # Pre-populate batting if not exists
            cur.execute("SELECT 1 FROM batting_scorecard WHERE match_id=? AND player_id=?", (match_id, pid))
            if not cur.fetchone():
                cur.execute("INSERT INTO batting_scorecard (match_id, team_id, player_id, dismissal_type) VALUES (?, ?, ?, 'DNB')", (match_id, t_id, pid))
                
            # Pre-populate bowling if not exists
            cur.execute("SELECT 1 FROM bowling_scorecard WHERE match_id=? AND player_id=?", (match_id, pid))
            if not cur.fetchone():
                cur.execute("INSERT INTO bowling_scorecard (match_id, team_id, player_id) VALUES (?, ?, ?)", (match_id, t_id, pid))

    for i, innings in enumerate(scorecard_data, start=1):
        # Determine current batting team
        batting_team_name = innings.get("team", "Unknown")
        batting_team_id = get_or_create_team(conn, batting_team_name)
        
        # Bowling team is the other team
        bowling_team_id = team2_id if batting_team_id == team1_id else team1_id
        
        # ---------------- MATCH TOTALS ----------------
        prefix = "team1" if batting_team_id == team1_id else "team2"
        try:
            total_data = innings.get("total", {})
            if total_data:
                cur.execute(f"UPDATE matches SET {prefix}_runs = ?, {prefix}_wickets = ?, {prefix}_overs = ? WHERE match_id = ?", 
                           (safe_int(total_data.get("runs")), safe_int(total_data.get("wickets")), safe_float(total_data.get("overs")), match_id))
        except Exception as e:
            print(f"⚠️ Failed to update match totals: {e}")

        # ---------------- BATTING ----------------
        for b in innings.get("batting", []):
            pid = get_or_create_player(conn, b["name"])
            
            bowler_name = b.get("bowler")
            bowler_id = None
            if bowler_name:
                bowler_id = get_or_create_player(conn, bowler_name)

            cur.execute("""
                UPDATE batting_scorecard SET
                    team_id = ?, runs_scored = ?, balls_faced = ?, fours = ?, sixes = ?, strike_rate = ?, dismissal_type = ?, bowler_id = ?
                WHERE match_id = ? AND player_id = ?
            """, (
                batting_team_id, safe_int(b.get("runs")), safe_int(b.get("balls")), safe_int(b.get("4s")), safe_int(b.get("sixes")), safe_float(b.get("sr")), b.get("dismissal"), bowler_id,
                match_id, pid
            ))
            
            # If not in XI (fallback), insert it
            if cur.rowcount == 0:
                cur.execute("INSERT INTO batting_scorecard (match_id, team_id, player_id, runs_scored, balls_faced, fours, sixes, strike_rate, dismissal_type, bowler_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                           (match_id, batting_team_id, pid, safe_int(b.get("runs")), safe_int(b.get("balls")), safe_int(b.get("4s")), safe_int(b.get("sixes")), safe_float(b.get("sr")), b.get("dismissal"), bowler_id))

        # ---------------- BOWLING ----------------
        for bw in innings.get("bowling", []):
            pid = get_or_create_player(conn, bw["name"])
            
            cur.execute("""
                UPDATE bowling_scorecard SET
                    team_id = ?, overs = ?, runs_conceded = ?, wickets = ?, economy = ?
                WHERE match_id = ? AND player_id = ?
            """, (
                bowling_team_id, safe_float(bw.get("overs")), safe_int(bw.get("runs")), safe_int(bw.get("wickets")), safe_float(bw.get("economy")),
                match_id, pid
            ))
            
            # If not in XI, insert it
            if cur.rowcount == 0:
                cur.execute("INSERT INTO bowling_scorecard (match_id, team_id, player_id, overs, runs_conceded, wickets, economy) VALUES (?,?,?,?,?,?,?)",
                           (match_id, bowling_team_id, pid, safe_float(bw.get("overs")), safe_int(bw.get("runs")), safe_int(bw.get("wickets")), safe_float(bw.get("economy"))))

    conn.commit()
