import sqlite3

DB_NAME = "cricket.db"


conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON;")

# -------------------------------
# EVENTS
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY,
    event_name TEXT NOT NULL,
    format TEXT CHECK (format IN ('T20','ODI','TEST')),
    season_year INTEGER
);
""")

# -------------------------------
# TEAMS
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY,
    team_name TEXT NOT NULL UNIQUE,
    country_name TEXT NOT NULL
);
""")

# -------------------------------
# PLAYERS
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    country_name TEXT,
    date_of_birth DATE,
    birth_place TEXT,
    primary_role TEXT,
    batting_style TEXT,
    bowling_style TEXT
);
""")

# -------------------------------
# VENUES
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS venues (
    venue_id INTEGER PRIMARY KEY,
    stadium_name TEXT NOT NULL,
    city TEXT NOT NULL,
    seating_capacity INTEGER
);
""")

# -------------------------------
# MATCHES
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,

    match_code TEXT UNIQUE,
    match_number TEXT,

    team1_id INTEGER NOT NULL,
    team2_id INTEGER NOT NULL,

    venue_id INTEGER,
    match_date DATE,
    match_time TEXT,

    toss_winner_team_id INTEGER,
    toss_decision TEXT CHECK (toss_decision IN ('bat','field')),

    match_status TEXT CHECK (
        match_status IN ('scheduled','completed','abandoned','no_result','cancelled')
    ),

    winning_team_id INTEGER,
    result_text TEXT,

    player_of_match_id INTEGER,

    -- TEAM 1 SCORE
    team1_runs INTEGER,
    team1_wickets INTEGER,
    team1_overs REAL,

    -- TEAM 2 SCORE
    team2_runs INTEGER,
    team2_wickets INTEGER,
    team2_overs REAL,

    FOREIGN KEY (event_id) REFERENCES events(event_id),
    FOREIGN KEY (team1_id) REFERENCES teams(team_id),
    FOREIGN KEY (team2_id) REFERENCES teams(team_id),
    FOREIGN KEY (venue_id) REFERENCES venues(venue_id),
    FOREIGN KEY (toss_winner_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (winning_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_of_match_id) REFERENCES players(player_id),

    CHECK (team1_id != team2_id)
);
""")

# -------------------------------
# PLAYING XI
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS playing_xi (
    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,

    PRIMARY KEY (match_id, team_id, player_id),

    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
""")

# -------------------------------
# MATCH PLAYER ROLES (NEW)
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS match_player_roles (
    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    role_type TEXT NOT NULL CHECK (
        role_type IN ('captain','wicketkeeper')
    ),

    PRIMARY KEY (match_id, team_id, role_type),

    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
""")

# -------------------------------
# OFFICIALS
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS officials (
    official_id INTEGER PRIMARY KEY,
    official_name TEXT NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS match_officials (
    match_id INTEGER NOT NULL,
    official_id INTEGER NOT NULL,
    role_type TEXT CHECK (
        role_type IN ('umpire','third_umpire','referee')
    ),

    PRIMARY KEY (match_id, official_id, role_type),

    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (official_id) REFERENCES officials(official_id)
);
""")

# -------------------------------
# BATTING SCORECARD
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS batting_scorecard (
    batting_id INTEGER PRIMARY KEY,

    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,

    runs_scored INTEGER,
    balls_faced INTEGER,
    fours INTEGER,
    sixes INTEGER,
    strike_rate REAL,

    dismissal_type TEXT,
    bowler_id INTEGER,

    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (bowler_id) REFERENCES players(player_id)
);
""")

# -------------------------------
# BOWLING SCORECARD
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS bowling_scorecard (
    bowling_id INTEGER PRIMARY KEY,

    match_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,

    overs REAL,
    runs_conceded INTEGER,
    wickets INTEGER,
    maidens INTEGER,
    economy REAL,

    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
""")

# -------------------------------
# INDEXES (PERFORMANCE)
# -------------------------------
cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_event ON matches(event_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_batting_match ON batting_scorecard(match_id);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_bowling_match ON bowling_scorecard(match_id);")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_player_match ON batting_scorecard(player_id, match_id);")

conn.commit()
conn.close()

print("✅ Final production-ready database created:", DB_NAME)

