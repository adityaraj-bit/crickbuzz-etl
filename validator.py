def validate_match_data(match, scorecard, info):
    errors = []

    # ---------------- MATCH ----------------
    if not match.get("link"):
        errors.append("Missing match link")

    # ---------------- SCORECARD ----------------
    if not scorecard:
        errors.append("Scorecard is None")

    else:
        if len(scorecard) < 2:
            errors.append("Less than 2 innings")

        for i, innings in enumerate(scorecard):
            if not innings:
                errors.append(f"Innings {i} is None")
                continue

            if not innings.get("team"):
                errors.append(f"Innings {i} missing team")

            if not innings.get("batting"):
                errors.append(f"Innings {i} missing batting")

            if not innings.get("bowling"):
                errors.append(f"Innings {i} missing bowling")

    # ---------------- INFO ----------------
    if info:
        if "squads" not in info:
            errors.append("Info exists but squads missing")

    return errors