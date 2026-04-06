from match_list import get_matches
from match_details import get_match_details
from scorecard import parse_scorecard
from match_info import parse_match_info
from player_profile import scrape_player_profile

from db import (
    get_conn, create_match, get_or_create_team, get_or_create_player, 
    ensure_defaults, get_or_create_event, get_or_create_venue, 
    insert_match_official, insert_playing_xi, update_match_result,
    update_match_player_of_match, insert_match_player_role
)
from insert_scorecard import insert_scorecard
import traceback
from validator import validate_match_data
from utils import normalize_name, normalize_date
import re

def debug(label, value=None):
    print(f"\n🔍 DEBUG → {label}")
    if value is not None:
        print(value)


def clean_name(name):
    return (
        name.replace("(c)", "")
            .replace("(wk)", "")
            .replace("(c & wk)", "")
            .strip()
    )


player_cache = {}

def get_or_create_player_with_profile(conn, player):
    # 'player' is a dict: {"name": "...", "profile": "...", "roles": [...]}
    name = normalize_name(player["name"])

    if name in player_cache:
        return player_cache[name]

    profile_data = None
    if player.get("profile"):
        try:
            debug(f"SCRAPING PROFILE: {name}", player["profile"])
            profile_data = scrape_player_profile(player["profile"])
        except Exception as e:
            print(f"⚠️ Failed to scrape profile for {name}: {e}")

    pid = get_or_create_player(conn, name, profile_data)
    player_cache[name] = pid
    return pid

def run():
    conn = get_conn()
    ensure_defaults(conn)

    matches = get_matches()
    debug(f"TOTAL MATCHES FOUND: {len(matches)}")

    for match in matches:
        try:
            print(f"\n🚀 {match['match']}")
            debug("MATCH OBJECT", match)

            # --- PRE-SCAN FOR STATUS ---
            status_text = match.get("status", "").lower()
            is_abandoned = any(word in status_text for word in ["abandoned", "no result", "cancelled"])
            
            # 1. Early IDENTIFICATION
            match_code = match["link"].split("/")[-1]
            series_name = match.get("series", "Default Event")
            
            # 2. Get/Create Event & Venue (Even for abandoned)
            event_id = get_or_create_event(conn, series_name)
            debug("EVENT ID", event_id)

            details = get_match_details(match["link"])
            debug("DETAILS", details)

            info_url = details.get("info_url") if details else None
            scorecard_url = details.get("scorecard_url") if details else None

            # 3. Handle TEAMS (More Robustly)
            team1_name = match.get("team1", "Unknown")
            team2_name = match.get("team2", "Unknown")

            if team1_name == "Unknown" or team2_name == "Unknown":
                if " vs " in match["match"]:
                    parts = match["match"].split(",")[0].split(" vs ")
                    if len(parts) >= 2:
                        team1_name = parts[0].strip()
                        team2_name = parts[1].strip()
            
            team1_id = get_or_create_team(conn, team1_name)
            team2_id = get_or_create_team(conn, team2_name)

            # 4. Create/Update Match Entry EARLY
            match_status = "abandoned" if is_abandoned else "completed"
            match_number = None
            if "," in match["match"]:
                match_number = match["match"].split(",")[-1].strip()

            # Attempt info parsing for venue and time/date
            info = None
            venue_id = 1
            match_time = None
            match_date = None
            
            if info_url:
                info = parse_match_info(info_url)
                if info:
                    info_data = info.get("info", {})
                    venue_lookup = {**info_data, **info.get("venue", {})}
                    venue_id = get_or_create_venue(conn, venue_lookup)
                    
                    # 1. Extract Time
                    match_time = info_data.get("Time")
                    
                    # 2. Extract Date (Robustly)
                    raw_date = info_data.get("Date")
                    if raw_date:
                        # Extract year from series name (e.g. "Series Name, 2024")
                        year_match = re.search(r"\b(20\d{2})\b", series_name)
                        year = year_match.group(1) if year_match else None
                        match_date = normalize_date(raw_date, year)

            match_id = create_match(conn, match_code, team1_id, team2_id, 
                                    event_id=event_id, venue_id=venue_id, 
                                    match_number=match_number, status=match_status,
                                    match_time=match_time, match_date=match_date)
            debug("MATCH ID", match_id)

            if is_abandoned:
                print("⚠️ Match was abandoned/cancelled → Match entry created, skipping deeper parsing.")
                conn.commit()
                continue

            if not scorecard_url:
                debug("NO SCORECARD → SKIP DEEPER PARSING")
                continue

            # 5. Full Parsing (for Completed Matches)
            scorecard = parse_scorecard(scorecard_url)
            if not scorecard:
                debug("SCORECARD IS NONE → SKIP DEEPER PARSING")
                continue
            
            # Validation (Optional)
            errors = validate_match_data(match, scorecard, info)
            if errors:
                print("\n⚠️ VALIDATION FAILED:")
                for e in errors: print(" -", e)

            # ---------------- STEP 7 ----------------
            # Get Metadata from Info page
            metadata = info.get("info", {}) if info else {}
            
            match_players = {} # Store name -> pid for MOTM resolution
            
            # --- Identify and Sync 11 Players for each team from Scorecard ---
            team_players_list = {} # team_name -> list of player dicts
            
            for innings in scorecard:
                t_name = innings["team"]
                if t_name not in team_players_list:
                    team_players_list[t_name] = []
                
                # Collect from batting and dnb
                participants = innings.get("batting", []) + innings.get("dnb", [])
                for p in participants:
                    # Clean the name to ensure it matches
                    p["name"] = clean_name(p["name"])
                    
                    # Avoid duplicates in our tracking list
                    if not any(tp["name"] == p["name"] for tp in team_players_list[t_name]):
                        team_players_list[t_name].append(p)
            
            # Sync All Identified Players
            for t_name, players in team_players_list.items():
                t_id = get_or_create_team(conn, t_name)
                for p_obj in players:
                    pid = get_or_create_player_with_profile(conn, p_obj)
                    if pid:
                        # Store name -> pid for MOTM resolution
                        match_players[normalize_name(p_obj["name"])] = pid
                        
                        # Ensure in playing_xi table
                        insert_playing_xi(conn, match_id, t_id, pid)
                        
                        # Record Roles (Captain, WK)
                        roles = p_obj.get("roles", [])
                        for role in roles:
                            insert_match_player_role(conn, match_id, t_id, pid, role)

            debug("PLAYER SYNC DONE")

            # ---------------- STEP 8 ----------------
            # Official Info & Result Parsing
            umpires = metadata.get("Umpires", "")
            referee = metadata.get("Referee", "")
            toss_str = metadata.get("Toss", "")
            
            # Officials
            if umpires:
                for u in umpires.split(","):
                    insert_match_official(conn, match_id, u.strip(), "umpire")
            
            if metadata.get("3rd Umpire"):
                insert_match_official(conn, match_id, metadata.get("3rd Umpire"), "third_umpire")
            if referee:
                insert_match_official(conn, match_id, referee, "referee")
            
            # --- ROBUST PARSING LOGIC ---
            def find_team_in_string(text, teams_list):
                if not text: return None
                text_lower = text.lower()
                for target_team in teams_list:
                    if target_team.lower() in text_lower:
                        return target_team
                return None

            match_teams = [team1_name, team2_name]
            
            # 1. Toss Logic
            toss_winner_id = None
            toss_decision = None
            if toss_str:
                debug("TOSS STRING FOUND", toss_str)
                winner_name = find_team_in_string(toss_str, match_teams)
                if winner_name:
                    toss_winner_id = get_or_create_team(conn, winner_name)
                
                t_lower = toss_str.lower()
                if "field" in t_lower or "bowl" in t_lower:
                    toss_decision = "field"
                elif "bat" in t_lower:
                    toss_decision = "bat"
                
                debug(f"PARSED TOSS: WinnerID={toss_winner_id}, Decision={toss_decision}")
                update_match_result(conn, match_id, toss_winner_id=toss_winner_id, toss_decision=toss_decision)

            # 2. Result Logic
            result_str = metadata.get("Result") or match.get("status", "")
            winner_id = None
            if result_str:
                debug("RESULT STRING FOUND", result_str)
                if any(word in result_str.lower() for word in ["won by", "beat", "win"]):
                    win_name = find_team_in_string(result_str, match_teams)
                    if win_name:
                        winner_id = get_or_create_team(conn, win_name)
            
            debug(f"PARSED WINNER: WinnerID={winner_id}")
            
            new_time = metadata.get("Time")
            update_match_result(conn, match_id, winner_id=winner_id, result_text=result_str, 
                                match_time=new_time)

            # Player of the Match
            motm_name = details.get("player_of_match")
            if motm_name:
                motm_norm = normalize_name(motm_name)
                debug("PLAYER OF THE MATCH", motm_norm)
                
                motm_id = match_players.get(motm_norm)
                if not motm_id:
                    motm_id = get_or_create_player(conn, motm_name)
                
                update_match_player_of_match(conn, match_id, motm_id)

            # ---------------- STEP 9 ----------------
            conn.commit()
            
            debug("INSERT SCORECARD START")
            insert_scorecard(conn, match_id, team1_id, team2_id, scorecard)
            debug("INSERT SCORECARD DONE")

            # ---------------- STEP 11 ----------------
            # Final participation check: ensure all Playing XI have some scoreboard presence 
            # (backfill if they didn't bat or bowl)
            cur = conn.cursor()
            for t_name, players in team_players_list.items():
                t_id = get_or_create_team(conn, t_name)
                for p_obj in players:
                    p_pid = match_players.get(normalize_name(p_obj["name"]))
                    if not p_pid: continue
                    
                    # Ensure in batting_scorecard
                    cur.execute("SELECT 1 FROM batting_scorecard WHERE match_id=? AND player_id=?", (match_id, p_pid))
                    if not cur.fetchone():
                        cur.execute("""
                            INSERT INTO batting_scorecard (match_id, team_id, player_id, dismissal_type)
                            VALUES (?, ?, ?, 'did not bat')
                        """, (match_id, t_id, p_pid))
                    
                    # Ensure in bowling_scorecard (backfill with 0s)
                    cur.execute("SELECT 1 FROM bowling_scorecard WHERE match_id=? AND player_id=?", (match_id, p_pid))
                    if not cur.fetchone():
                        cur.execute("""
                            INSERT INTO bowling_scorecard (match_id, team_id, player_id, overs, runs_conceded, wickets, economy)
                            VALUES (?, ?, ?, 0.0, 0, 0, 0.0)
                        """, (match_id, t_id, p_pid))
            
            conn.commit()
            print("✅ Stored")

        except Exception as e:
            print("\n❌ ERROR OCCURRED")
            traceback.print_exc()
            continue

    conn.close()


if __name__ == "__main__":
    run()
