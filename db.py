import sqlite3
from utils import normalize_name

DB_NAME = "cricket.db"


# -------------------------------
# CONNECTION
# -------------------------------
def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# -------------------------------
# TEAM
# -------------------------------
def get_or_create_team(conn, team_name):
    cur = conn.cursor()

    cur.execute("SELECT team_id FROM teams WHERE team_name=?", (team_name,))
    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute("""
        INSERT INTO teams (team_name, country_name)
        VALUES (?, ?)
    """, (team_name, team_name))

    conn.commit()
    return cur.lastrowid


# -------------------------------
# PLAYER
# -------------------------------
def get_or_create_player(conn, full_name, profile_data=None):
    cur = conn.cursor()

    norm_name = normalize_name(full_name)

    cur.execute("""
        SELECT player_id FROM players
        WHERE full_name=?
    """, (norm_name,))

    row = cur.fetchone()
    if row:
        return row[0]

    # profile fallback
    country = "Unknown"
    dob = None
    birth_place = None
    batting = None
    bowling = None

    if profile_data:
        country = profile_data.get("country", "Unknown")
        
        info = profile_data.get("personal_info", {})
        dob = info.get("Born")
        birth_place = info.get("Birth Place")
        batting = info.get("Batting Style")
        bowling = info.get("Bowling Style")

    cur.execute("""
        INSERT INTO players (
            full_name,
            country_name,
            date_of_birth,
            birth_place,
            batting_style,
            bowling_style
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        norm_name,
        country,
        dob,
        birth_place,
        batting,
        bowling
    ))

    conn.commit()
    return cur.lastrowid


# -------------------------------
# VENUE
# -------------------------------
def get_or_create_venue(conn, venue_data):
    cur = conn.cursor()

    # Try different possible keys from Cricbuzz
    stadium = venue_data.get("Stadium") or venue_data.get("Venue") or "Unknown Stadium"
    city = venue_data.get("City", "Unknown")
    capacity_str = str(venue_data.get("Capacity", "0"))
    
    # If 'Venue' was used (e.g. "Basin Reserve, Wellington"), try to split it
    if stadium != "Unknown Stadium" and "," in stadium and city == "Unknown":
        parts = stadium.split(",")
        stadium = parts[0].strip()
        city = parts[1].strip()

    # Clean capacity
    import re
    capacity = 0
    match = re.search(r'\d+', capacity_str.replace(",", ""))
    if match:
        capacity = int(match.group())

    # Try to find existing
    cur.execute("""
        SELECT venue_id FROM venues 
        WHERE stadium_name = ? AND city = ?
    """, (stadium, city))
    
    row = cur.fetchone()
    if row:
        return row[0]

    # Create new
    try:
        cur.execute("""
            INSERT INTO venues (stadium_name, city, seating_capacity)
            VALUES (?, ?, ?)
        """, (stadium, city, capacity))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"❌ Failed to create venue '{stadium}': {e}")
        return 1 # Fallback to default unknown venue


# -------------------------------
# EVENT
# -------------------------------
def get_or_create_event(conn, event_name, format='T20', season_year=2026):
    cur = conn.cursor()
    
    # Try to find existing
    cur.execute("SELECT event_id FROM events WHERE event_name = ?", (event_name,))
    row = cur.fetchone()
    if row:
        return row[0]
        
    # Create new
    try:
        cur.execute("""
            INSERT INTO events (event_name, format, season_year)
            VALUES (?, ?, ?)
        """, (event_name, format, season_year))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"❌ Failed to create event '{event_name}': {e}")
        return 1 # Fallback to default event


# -------------------------------
# MATCH
# -------------------------------
def create_match(conn, match_code, team1_id, team2_id, event_id=1, venue_id=1):
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO matches (
                event_id,
                match_code,
                team1_id,
                team2_id,
                venue_id,
                match_date,
                match_status
            )
            VALUES (?, ?, ?, ?, ?, DATE('now'), 'scheduled')
        """, (event_id, match_code, team1_id, team2_id, venue_id))

        conn.commit()

    except Exception as e:
        print("❌ INSERT FAILED:", e)

    cur.execute("SELECT match_id FROM matches WHERE match_code=?", (match_code,))
    row = cur.fetchone()

    if not row:
        print("❌ CRITICAL: match not found after insert:", match_code)
        return None

    return row[0]


# -------------------------------
# OFFICIALS
# -------------------------------
def get_or_create_official(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT official_id FROM officials WHERE official_name = ?", (name,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("INSERT INTO officials (official_name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


def insert_match_official(conn, match_id, name, role):
    if not name:
        return
        
    cur = conn.cursor()
    oid = get_or_create_official(conn, name)
    
    try:
        cur.execute("""
            INSERT OR REPLACE INTO match_officials (match_id, official_id, role_type)
            VALUES (?, ?, ?)
        """, (match_id, oid, role))
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to insert match official '{name}': {e}")


# -------------------------------
# MATCH HELPERS
# -------------------------------
def insert_playing_xi(conn, match_id, team_id, player_id):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR REPLACE INTO playing_xi (match_id, team_id, player_id)
            VALUES (?, ?, ?)
        """, (match_id, team_id, player_id))
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to insert playing XI {player_id}: {e}")


def update_match_result(conn, match_id, winner_id=None, toss_winner_id=None, toss_decision=None, result_text=None):
    cur = conn.cursor()
    try:
        if winner_id:
            cur.execute("UPDATE matches SET winning_team_id = ?, match_status = 'completed' WHERE match_id = ?", (winner_id, match_id))
        
        if toss_winner_id and toss_decision:
            cur.execute("UPDATE matches SET toss_winner_team_id = ?, toss_decision = ? WHERE match_id = ?", (toss_winner_id, toss_decision, match_id))
            
        if result_text:
            cur.execute("UPDATE matches SET result_text = ? WHERE match_id = ?", (result_text, match_id))
            
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to update match result for {match_id}: {e}")


def update_match_player_of_match(conn, match_id, player_id):
    cur = conn.cursor()
    try:
        cur.execute("UPDATE matches SET player_of_match_id = ? WHERE match_id = ?", (player_id, match_id))
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to update player of match for {match_id}: {e}")


def insert_match_player_role(conn, match_id, team_id, player_id, role_type):
    if not role_type or role_type.lower() not in ['captain', 'wicketkeeper']:
        return

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR REPLACE INTO match_player_roles (match_id, team_id, player_id, role_type)
            VALUES (?, ?, ?, ?)
        """, (match_id, team_id, player_id, role_type.lower()))
        conn.commit()
    except Exception as e:
        print(f"❌ Failed to insert match player role: {e}")


def ensure_defaults(conn):
    cur = conn.cursor()

    # EVENT
    cur.execute("""
        INSERT OR IGNORE INTO events (
            event_id, event_name, format, season_year
        )
        VALUES (1, 'Default Event', 'T20', 2026)
    """)

    # VENUE
    cur.execute("""
        INSERT OR IGNORE INTO venues (
            venue_id, stadium_name, city, seating_capacity
        )
        VALUES (1, 'Unknown Stadium', 'Unknown', 0)
    """)

    conn.commit()

