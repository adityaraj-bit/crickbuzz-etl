from db import get_or_create_player, get_or_create_team
from utils import safe_int, safe_float


def insert_scorecard(conn, match_id, team1_id, team2_id, scorecard_data):
    cur = conn.cursor()

    for i, innings in enumerate(scorecard_data, start=1):
        # Determine current team
        team_name = innings.get("team", "Unknown")
        team_id = get_or_create_team(conn, team_name)
        
        # ---------------- MATCH TOTALS ----------------
        # Update match summary scores in the flat matches table
        # We assume innings 1 = Team 1, innings 2 = Team 2
        prefix = "team1" if i == 1 else "team2"
        
        try:
            # We don't have total runs/wickets/overs in the current scorecard_data.
            # Usually these are extracted from the header or a separate 'total' row.
            # For now, we'll try to find a 'total' key if it exists, or just skip.
            total_data = innings.get("total", {})
            if total_data:
                cur.execute(f"""
                    UPDATE matches 
                    SET {prefix}_runs = ?, {prefix}_wickets = ?, {prefix}_overs = ?
                    WHERE match_id = ?
                """, (
                    safe_int(total_data.get("runs")),
                    safe_int(total_data.get("wickets")),
                    safe_float(total_data.get("overs")),
                    match_id
                ))
        except Exception as e:
            print(f"⚠️ Failed to update match totals for {prefix}: {e}")

        # ---------------- BATTING ----------------
        for b in innings.get("batting", []):
            pid = get_or_create_player(conn, b["name"])

            # Avoid duplicates (composite PK not enforced on batting_id, but good practice)
            cur.execute("""
                SELECT batting_id FROM batting_scorecard 
                WHERE match_id = ? AND team_id = ? AND player_id = ?
            """, (match_id, team_id, pid))
            
            # Resolve bowler_id if present
            bowler_name = b.get("bowler")
            bowler_id = None
            if bowler_name:
                bowler_id = get_or_create_player(conn, bowler_name)

            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO batting_scorecard (
                        match_id, team_id, player_id,
                        runs_scored, balls_faced,
                        fours, sixes,
                        strike_rate, dismissal_type, bowler_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_id,
                    team_id,
                    pid,
                    safe_int(b.get("runs")),
                    safe_int(b.get("balls")),
                    safe_int(b.get("4s")),
                    safe_int(b.get("sixes")),
                    safe_float(b.get("sr")),
                    b.get("dismissal"),
                    bowler_id
                ))

        # ---------------- BOWLING ----------------
        for b in innings.get("bowling", []):
            pid = get_or_create_player(conn, b["name"])

            cur.execute("""
                SELECT bowling_id FROM bowling_scorecard 
                WHERE match_id = ? AND team_id = ? AND player_id = ?
            """, (match_id, team_id, pid))

            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO bowling_scorecard (
                        match_id, team_id, player_id,
                        overs, runs_conceded, wickets, economy
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    match_id,
                    team_id,
                    pid,
                    safe_float(b.get("overs")),
                    safe_int(b.get("runs")),
                    safe_int(b.get("wickets")),
                    safe_float(b.get("economy"))
                ))

    conn.commit()
