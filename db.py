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
    if not full_name or not str(full_name).strip():
        return None

    cur = conn.cursor()
    norm_name = normalize_name(full_name)

    if not norm_name:
        return None

    cur.execute("""
        SELECT player_id FROM players
        WHERE full_name=?
    """, (norm_name,))

    row = cur.fetchone()
    
    # -------------------------------
    # 1. EXTRACT DATA FROM profile_data
    # -------------------------------
    country = "Unknown"
    dob = None
    birth_place = None
    role = None
    batting = None
    bowling = None
    
    if isinstance(profile_data, dict):
        from utils import normalize_dob
        country = profile_data.get("country", "Unknown")
        info = profile_data.get("personal_info", {})
        dob = normalize_dob(info.get("Born"))
        birth_place = info.get("Birth Place")
        role = info.get("Role")
        batting = info.get("Batting Style")
        bowling = info.get("Bowling Style")

    # -------------------------------
    # 2. UPDATE OR INSERT
    # -------------------------------
    if row:
        player_id = row[0]
        # Update existing player if profile_data is provided (ensures missing info is filled)
        if profile_data:
            try:
                # Use NULLIF for country to allow 'Unknown' to be replaced
                cur.execute("""
                    UPDATE players 
                    SET country_name = CASE WHEN country_name IS NULL OR country_name = 'Unknown' THEN ? ELSE country_name END,
                        date_of_birth = COALESCE(date_of_birth, ?),
                        birth_place = COALESCE(birth_place, ?),
                        primary_role = COALESCE(primary_role, ?),
                        batting_style = COALESCE(batting_style, ?),
                        bowling_style = COALESCE(bowling_style, ?)
                    WHERE player_id = ?
                """, (country, dob, birth_place, role, batting, bowling, player_id))
                conn.commit()
            except Exception as e:
                print(f"⚠️ Failed to update player profile for {norm_name}: {e}")
        return player_id

    cur.execute("""
        INSERT INTO players (
            full_name,
            country_name,
            date_of_birth,
            birth_place,
            primary_role,
            batting_style,
            bowling_style
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        norm_name,
        country,
        dob,
        birth_place,
        role,
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
    city_raw = venue_data.get("City", "Unknown")
    capacity_str = str(venue_data.get("Capacity", "0"))
    
    city = city_raw
    country = "Unknown"

    # Split "City, Country" if present (e.g. "Windhoek, Namibia")
    if "," in city_raw:
        parts = city_raw.split(",")
        city = parts[0].strip()
        country = parts[1].strip()

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
        WHERE stadium_name = ? AND city = ? AND country = ?
    """, (stadium, city, country))
    
    row = cur.fetchone()
    if row:
        return row[0]

    # Create new
    try:
        cur.execute("""
            INSERT INTO venues (stadium_name, city, country, seating_capacity)
            VALUES (?, ?, ?, ?)
        """, (stadium, city, country, capacity))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"❌ Failed to create venue '{stadium}': {e}")
        return 1


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
def create_match(conn, match_code, team1_id, team2_id, event_id=1, venue_id=1, match_number=None, status='scheduled', match_time=None, match_date=None):
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
                match_time,
                match_status,
                match_number
            )
            VALUES (?, ?, ?, ?, ?, COALESCE(?, DATE('now')), ?, ?, ?)
        """, (event_id, match_code, team1_id, team2_id, venue_id, match_date, match_time, status, match_number))

        conn.commit()

    except sqlite3.IntegrityError:
        # Match already exists, update the match_number
        try:
            cur.execute("""
                UPDATE matches 
                SET match_number = ?, 
                    match_time = COALESCE(?, match_time),
                    match_date = COALESCE(?, match_date)
                WHERE match_code = ?
            """, (match_number, match_time, match_date, match_code))
            conn.commit()
        except Exception as e:
            print(f"❌ UPDATE FAILED for existing match {match_code}:", e)

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


def update_match_result(conn, match_id, winner_id=None, toss_winner_id=None, toss_decision=None, result_text=None, match_time=None):
    cur = conn.cursor()
    try:
        if winner_id:
            cur.execute("UPDATE matches SET winning_team_id = ?, match_status = 'completed' WHERE match_id = ?", (winner_id, match_id))
        
        if toss_winner_id and toss_decision:
            cur.execute("UPDATE matches SET toss_winner_team_id = ?, toss_decision = ? WHERE match_id = ?", (toss_winner_id, toss_decision, match_id))
            
        if result_text:
            cur.execute("UPDATE matches SET result_text = ? WHERE match_id = ?", (result_text, match_id))
            
        if match_time:
            cur.execute("UPDATE matches SET match_time = ? WHERE match_id = ?", (match_time, match_id))
            
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

