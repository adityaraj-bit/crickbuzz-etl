from match_list import get_matches
from match_details import get_match_details
from scorecard import parse_scorecard
from match_info import parse_match_info

from db import (
    get_conn, create_match, get_or_create_team, get_or_create_player, 
    ensure_defaults, get_or_create_event, get_or_create_venue, 
    insert_match_official, insert_playing_xi, update_match_result,
    update_match_player_of_match, insert_match_player_role
)
from insert_scorecard import insert_scorecard
from player_profile import scrape_player_profile
import traceback
from validator import validate_match_data

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
    name = clean_name(player["name"])

    if name in player_cache:
        return player_cache[name]

    profile = None

    if player.get("profile"):
        try:
            profile = scrape_player_profile(player["profile"])
        except:
            profile = None

    pid = get_or_create_player(conn, name, profile)

    player_cache[name] = pid
    return pid

def run():
    conn = get_conn()
    ensure_defaults(conn)

    matches = get_matches()

    for match in matches:
        try:
            print(f"\n🚀 {match['match']}")

            # ---------------- STEP 1 ----------------
            debug("MATCH OBJECT", match)

            details = get_match_details(match["link"])
            debug("DETAILS", details)

            if not details:
                debug("DETAILS IS NONE → SKIP")
                continue

            # ---------------- STEP 2 ----------------
            scorecard_url = details.get("scorecard_url")
            info_url = details.get("info_url")

            debug("SCORECARD URL", scorecard_url)
            debug("INFO URL", info_url)

            if not scorecard_url:
                debug("NO SCORECARD → SKIP")
                continue

            # ---------------- STEP 3 ----------------
            scorecard = parse_scorecard(scorecard_url)
            debug("SCORECARD RAW", scorecard)

            if not scorecard:
                debug("SCORECARD IS NONE → SKIP")
                continue

            # ---------------- STEP 4 ----------------
            info = None
            if info_url:
                info = parse_match_info(info_url)

            debug("INFO RAW", info)

            # ---------------- STEP 5 ----------------
            if info and info.get("squads"):
                teams = list(info["squads"].keys())
                debug("TEAMS FROM INFO", teams)
            else:
                debug("FALLBACK → USING SCORECARD")

                teams = []
                for innings in scorecard:
                    if not innings:
                        debug("INVALID INNINGS FOUND", innings)
                        continue

                    team = innings.get("team")
                    debug("TEAM FROM INNINGS", team)

                    if team:
                        teams.append(team)

                teams = list(set(teams))

            debug("FINAL TEAMS", teams)

            if len(teams) < 2:
                debug("LESS THAN 2 TEAMS → SKIP")
                continue

            # ---------------- STEP 6 ----------------
            match_code = match["link"].split("/")[-1]
            debug("MATCH CODE", match_code)

            # Get or create event (series)
            series_name = match.get("series", "Default Event")
            event_id = get_or_create_event(conn, series_name)
            debug("EVENT ID", event_id)

            # Get or create venue
            # Merge both info and venue sections as Cricbuzz varies where it puts stadium data
            venue_lookup = {**info.get("info", {}), **info.get("venue", {})}
            venue_id = get_or_create_venue(conn, venue_lookup)
            debug("VENUE ID", venue_id)

            # Identify Team 1 and Team 2 from the match list or title
            # Format usually: "Team A vs Team B, ..."
            team1_name = "Unknown"
            team2_name = "Unknown"
            if " vs " in match["match"]:
                parts = match["match"].split(",")[0].split(" vs ")
                team1_name = parts[0].strip()
                team2_name = parts[1].strip()
            
            team1_id = get_or_create_team(conn, team1_name)
            team2_id = get_or_create_team(conn, team2_name)
            debug("TEAM IDs", f"{team1_id} vs {team2_id}")

            # Extract match number (e.g., "15th Match")
            match_number = None
            if "," in match["match"]:
                match_number = match["match"].split(",")[-1].strip()
            debug("MATCH NUMBER", match_number)

            match_id = create_match(conn, match_code, team1_id, team2_id, event_id=event_id, venue_id=venue_id, match_number=match_number)
            debug("MATCH ID", match_id)
            if not match_id:
                print("❌ match_id is None → skipping")
                continue
            errors = validate_match_data(match, scorecard, info)

            if errors:
                print("\n⚠️ VALIDATION FAILED:")
                for e in errors:
                    print(" -", e)
                continue
            # ---------------- STEP 7 ----------------
            match_players = {}
            if info and info.get("squads"):
                for team_name, squad in info["squads"].items():

                    debug("INSERT SQUAD", team_name)
                    curr_team_id = get_or_create_team(conn, team_name)
                    
                    # 1. Playing XI (Link table)
                    for player in squad.get("playing_xi", []):
                        pid = get_or_create_player_with_profile(conn, player)
                        insert_playing_xi(conn, match_id, curr_team_id, pid)
                        
                        # Store name -> pid for MOTM resolution
                        match_players[clean_name(player["name"])] = pid
                        
                        # 2. Specific Roles (Captain, WK)
                        role = player.get("role")
                        if role and role.lower() in ["captain", "wicketkeeper"]:
                            insert_match_player_role(conn, match_id, curr_team_id, pid, role)

            # ---------------- STEP 8 ----------------
            # Official Info Parsing
            info_all = info.get("info", {})
            
            # Officials
            umpires = info_all.get("Umpires", "")
            if umpires:
                for u in umpires.split(","):
                    insert_match_official(conn, match_id, u.strip(), "umpire")
            
            insert_match_official(conn, match_id, info_all.get("3rd Umpire"), "third_umpire")
            insert_match_official(conn, match_id, info_all.get("Referee"), "referee")
            
            # Toss & Result
            toss_str = info_all.get("Toss", "")
            result_str = info_all.get("Result", "")
            
            toss_winner_id = None
            toss_decision = None
            winner_id = None
            
            # Toss Logic: "Tanzania won the toss and opt to Bat"
            for t_name in info.get("squads", {}).keys():
                if t_name in toss_str:
                    toss_winner_id = get_or_create_team(conn, t_name)
                    toss_decision = 'bat' if 'opt to Bat' in toss_str else 'field'
                    break
            
            # Result Logic: "Tanzania won by 10 wickets"
            result_str = match.get("status", "")
            for t_name in info.get("squads", {}).keys():
                if t_name in result_str and "won by" in result_str:
                    winner_id = get_or_create_team(conn, t_name)
                    break
            
            # Result text (new column)
            result_text = result_str
            
            update_match_result(conn, match_id, winner_id, toss_winner_id, toss_decision, result_text=result_text)

            # Player of the Match
            motm_name = details.get("player_of_match")
            if motm_name:
                motm_clean = clean_name(motm_name)
                debug("PLAYER OF THE MATCH NAME", motm_clean)
                
                # Try to use existing player from squad
                motm_id = match_players.get(motm_clean)
                
                if not motm_id:
                    # Fallback to general lookup/create
                    motm_id = get_or_create_player_with_profile(conn, {"name": motm_name})
                
                debug("PLAYER OF THE MATCH ID", motm_id)
                update_match_player_of_match(conn, match_id, motm_id)

            # ---------------- STEP 9 ----------------
            
            conn.commit()
            # ---------------- STEP 8 ----------------
            debug("INSERT SCORECARD START")

            # Clean names in the scorecard data
            for innings in scorecard:
                if "batting" in innings:
                    for b in innings["batting"]:
                        b["name"] = clean_name(b["name"])

                if "bowling" in innings:
                    for bw in innings["bowling"]:
                        bw["name"] = clean_name(bw["name"])

            insert_scorecard(conn, match_id, team1_id, team2_id, scorecard)
            debug("INSERT SCORECARD DONE")

            print("✅ Stored")

        except Exception as e:
            print("\n❌ ERROR OCCURRED")
            traceback.print_exc()
            continue

    conn.close()


if __name__ == "__main__":
    run()