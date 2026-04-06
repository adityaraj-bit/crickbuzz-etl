# Cricbuzz ETL & Data Analysis Pipeline

A robust Python-based ETL (Extract, Transform, Load) pipeline for scraping cricket match data from Cricbuzz. The system extracts match metadata, player profiles, and detailed scorecards into a structured SQLite database and provides automated CSV exports for data analysis.

## Core Features

- Automated Scraping: Extracts match lists, detailed scorecards, and player profiles directly from Cricbuzz.
- Structured Database: Organizes data into a relational SQLite database with proper indexing for performance.
- Player Profile Sync: Scrapes and updates player-specific details including batting/bowling styles and birth information.
- Data Validation: Built-in validation checks to ensure data integrity during the scraping process.
- Enriched Data Exports: Generates both raw database dumps and human-readable "detailed" CSVs with SQL JOINs for easier analysis.

## Technology Stack

- Language: Python 3.x
- Data Storage: SQLite
- Libraries:
    - BeautifulSoup4 (Web Scraping)
    - Requests (HTTP Requests)
    - Selenium (Dynamic Content Handling)
    - CSV & OS (Data Export & File Management)

## Project Structure

- main.py: The primary orchestrator that runs the full ETL pipeline.
- db_creation.py: Initializes the SQLite database schema.
- db.py: Contains database helper functions and CRUD operations.
- csv_gen.py: Generates analytical CSV exports from the database.
- scorecard.py: Specialized parser for Cricbuzz scorecard pages.
- match_info.py: Parser for match metadata and venue details.
- player_profile.py: Scrapes detailed биографии information for players.
- squad_scraper.py: Handles squad and playing XI extraction.
- utils.py: Common utility functions for normalization and formatting.

## Installation

1. Clone the repository to your local machine.
2. Initialize a Python virtual environment:
   python -m venv venv
3. Activate the virtual environment:
   - Windows: venv\Scripts\activate
   - Mac/Linux: source venv/bin/activate
4. Install dependencies:
   pip install -r requirements.txt

## Usage Guide

### 1. Database Initialization
Ensure the database and tables are correctly set up:
python db_creation.py

### 2. Running the ETL Pipeline
To start scraping data and populating the database:
python main.py

### 3. Exporting Data to CSV
To generate readable data files for analysis:
python csv_gen.py

The exports will be saved in the csv_exports/ directory.

## Database Schema Overview

The system uses a relational schema designed for cricket data:

- events: Tournament and series information.
- teams: National and domestic team data.
- players: Detailed player profiles and statistics.
- venues: Stadium names, cities, and country locations.
- matches: Core match metadata (dates, times, toss, results).
- batting_scorecard: Ball-by-ball batting performance per match.
- bowling_scorecard: Bowling figures and wicket efficiency.
- playing_xi: match-specific team lineups.
- match_player_roles: Captains and wicketkeepers identification.
- officials: Umpires and match referees.

## Enriched CSV Exports

The csv_gen.py script produces specialized CSV files:

- detailed_matches.csv: Combines match results with team names and venue locations.
- detailed_batting.csv: Links batting performance with player names and match context.
- detailed_bowling.csv: Links bowling stats with player identities for better readability.
