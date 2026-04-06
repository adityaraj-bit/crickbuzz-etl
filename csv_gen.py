import sqlite3
import csv
import os

DB_NAME = "cricket.db"
OUTPUT_DIR = "csv_exports"


def export_all_data():
    """Main export function to generate both raw and enriched CSV files."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Export Enriched CSVs (Joined Data)
    print("--- 📊 Exporting Enriched Data ---")
    export_enriched_matches(cursor)
    export_enriched_batting(cursor)
    export_enriched_bowling(cursor)

    # 2. Export Raw Tables
    print("\n--- 🧱 Exporting Raw Tables ---")
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        export_table_to_csv(cursor, table)

    conn.close()
    print(f"\n✅ All exports completed. Files saved in '{OUTPUT_DIR}/'")


def export_enriched_matches(cursor):
    """Joins matches with teams, venues, and events for a readable summary."""
    sql = """
        SELECT 
            m.match_id,
            e.event_name,
            m.match_code,
            m.match_number,
            t1.team_name AS team1,
            t2.team_name AS team2,
            v.stadium_name AS venue,
            v.city,
            v.country,
            m.match_date,
            m.match_time,
            tw.team_name AS toss_winner,
            m.toss_decision,
            m.match_status,
            wt.team_name AS winner,
            m.result_text,
            p.full_name AS player_of_match
        FROM matches m
        LEFT JOIN events e ON m.event_id = e.event_id
        LEFT JOIN teams t1 ON m.team1_id = t1.team_id
        LEFT JOIN teams t2 ON m.team2_id = t2.team_id
        LEFT JOIN venues v ON m.venue_id = v.venue_id
        LEFT JOIN teams tw ON m.toss_winner_team_id = tw.team_id
        LEFT JOIN teams wt ON m.winning_team_id = wt.team_id
        LEFT JOIN players p ON m.player_of_match_id = p.player_id
    """
    write_query_to_csv(cursor, sql, "detailed_matches.csv")


def export_enriched_batting(cursor):
    """Joins batting scorecard with players and teams."""
    sql = """
        SELECT 
            b.batting_id,
            m.match_code,
            t.team_name,
            p.full_name AS player_name,
            b.runs_scored,
            b.balls_faced,
            b.fours,
            b.sixes,
            b.strike_rate,
            b.dismissal_type,
            bp.full_name AS bowler_name
        FROM batting_scorecard b
        JOIN matches m ON b.match_id = m.match_id
        JOIN teams t ON b.team_id = t.team_id
        JOIN players p ON b.player_id = p.player_id
        LEFT JOIN players bp ON b.bowler_id = bp.player_id
    """
    write_query_to_csv(cursor, sql, "detailed_batting.csv")


def export_enriched_bowling(cursor):
    """Joins bowling scorecard with players and teams."""
    sql = """
        SELECT 
            bo.bowling_id,
            m.match_code,
            t.team_name,
            p.full_name AS player_name,
            bo.overs,
            bo.runs_conceded,
            bo.wickets,
            bo.economy
        FROM bowling_scorecard bo
        JOIN matches m ON bo.match_id = m.match_id
        JOIN teams t ON bo.team_id = t.team_id
        JOIN players p ON bo.player_id = p.player_id
    """
    write_query_to_csv(cursor, sql, "detailed_bowling.csv")


def write_query_to_csv(cursor, query, filename):
    """Helper to execute query and write result to CSV."""
    cursor.execute(query)
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    
    file_path = os.path.join(OUTPUT_DIR, filename)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)
    print(f"✔ Exported: {filename} ({len(rows)} rows)")


def export_table_to_csv(cursor, table_name):
    """Standard export for any single table."""
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]

    file_path = os.path.join(OUTPUT_DIR, f"{table_name}.csv")
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(rows)
    print(f"✔ Exported Table: {table_name} ({len(rows)} rows)")


if __name__ == "__main__":
    export_all_data()
