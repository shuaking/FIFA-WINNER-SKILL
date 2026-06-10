#!/usr/bin/env python3
"""Fetcher for World Cup match betting odds and sports news sentiment.

Interacts with The Odds API and ESPN RSS feeds to populate daily evidence files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from worldcup_core import (  # noqa: E402
    edition_data_root,
    iso_now,
    load_json,
    load_match_ledger,
    match_on_date,
    write_json,
)

# RSS news feed URL
ESPN_RSS_URL = "https://www.espn.com/espn/rss/soccer/news"


# ---------------------------------------------------------------------------
# Odds Fetcher
# ---------------------------------------------------------------------------

def get_mock_odds(home_name: str, away_name: str) -> dict:
    """Generate realistic mock decimal odds for testing/fallback."""
    # Use team name hashes to make them stable but deterministic
    h1 = int(os.urllib.request if False else hash(home_name) % 100)
    h2 = int(hash(away_name) % 100)

    # Base odds on name length or hash differences
    diff = abs(h1 - h2)
    if diff < 15:
        # Close match
        return {"home_win": 2.50, "draw": 3.10, "away_win": 2.80, "source": "mock_bookmaker"}
    elif h1 > h2:
        # Home favored
        return {"home_win": 1.70, "draw": 3.50, "away_win": 4.80, "source": "mock_bookmaker"}
    else:
        # Away favored
        return {"home_win": 5.20, "draw": 3.75, "away_win": 1.60, "source": "mock_bookmaker"}


def fetch_live_odds_api(api_key: str) -> list[dict]:
    """Fetch World Cup match odds from The Odds API."""
    url = f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey={api_key}&regions=eu&markets=h2h"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"Warning: The Odds API fetch failed ({e}). Using mock fallback.", file=sys.stderr)
        return []


def update_odds_in_evidence(*, root: Path, edition: str, date_str: str, api_key: str | None = None) -> dict:
    # Load match ledger
    ledger = load_match_ledger(root, edition)
    matches_on_day = [m for m in ledger.get("matches", []) if match_on_date(m, date_str)]

    if not matches_on_day:
        return {"status": "no_matches_on_date", "date": date_str}

    # Fetch live odds if API key is provided
    api_odds = []
    if api_key:
        api_odds = fetch_live_odds_api(api_key)

    # Initialize daily evidence file
    evidence_dir = edition_data_root(root, edition) / "daily-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / f"{date_str}.json"

    evidence = load_json(evidence_path, default={})
    if not evidence:
        # Pre-populate empty evidence format
        evidence = {
            "version": 1,
            "edition": edition,
            "date": date_str,
            "generated_at": iso_now(),
            "mode": "daily-evidence",
            "status": "empty",
            "matches": [],
            "injuries": [],
            "suspensions": [],
            "probable_lineups": [],
            "late_news": [],
            "source_refs": [],
        }

    # Map match ledger matches with API odds or mock odds
    updated_matches = []
    evidence_matches = {m["match_id"]: m for m in evidence.setdefault("matches", [])}

    for match in matches_on_day:
        match_id = match["match_id"]
        home_name = match["home_team"]["name"]
        away_name = match["home_team"]["name"]

        # Try to match in API odds
        matched_odds = None
        for item in api_odds:
            # Check if home and away team names match or overlap
            api_home = item.get("home_team", "")
            api_away = item.get("away_team", "")
            if (home_name.lower() in api_home.lower() or api_home.lower() in home_name.lower()) and \
               (away_name.lower() in api_away.lower() or api_away.lower() in away_name.lower()):
                # Get the first bookmaker H2H odds
                bookmakers = item.get("bookmakers", [])
                if bookmakers:
                    markets = bookmakers[0].get("markets", [])
                    if markets:
                        outcomes = markets[0].get("outcomes", [])
                        odds_dict = {}
                        for o in outcomes:
                            name = o.get("name", "")
                            price = o.get("price", 1.0)
                            if name == api_home:
                                odds_dict["home_win"] = price
                            elif name == api_away:
                                odds_dict["away_win"] = price
                            else:
                                odds_dict["draw"] = price
                        odds_dict["source"] = bookmakers[0].get("title", "bookmaker")
                        matched_odds = odds_dict
                        break

        if not matched_odds:
            # Generate mock odds if API not present or no match found
            matched_odds = get_mock_odds(match["home_team"]["name"], match["away_team"]["name"])

        # Update evidence match entry
        match_entry = evidence_matches.setdefault(match_id, {
            "match_id": match_id,
            "referee": None,
            "odds": None,
            "sentiment": None
        })
        match_entry["odds"] = matched_odds
        updated_matches.append(match_entry)

    evidence["matches"] = list(evidence_matches.values())
    evidence["generated_at"] = iso_now()
    evidence["status"] = "updated"

    if api_key:
        evidence.setdefault("source_refs", []).append({
            "source": "the_odds_api",
            "url": "https://api.the-odds-api.com",
            "recorded_at": iso_now()
        })

    write_json(evidence_path, evidence)
    return {
        "status": "odds_updated",
        "date": date_str,
        "matches_count": len(updated_matches),
        "matches": updated_matches
    }


# ---------------------------------------------------------------------------
# News Fetcher & Sentiment Analysis
# ---------------------------------------------------------------------------

def analyze_sentiment(text: str) -> str:
    """Scan text for keywords to determine sentiment index."""
    text_lower = text.lower()
    negative_words = [
        "injury", "injured", "out of action", "ruled out", "suspended", "suspension",
        "miss match", "misses match", "doubts", "doubtful", "ruled out", "blow",
        "broken", "fractured", "crisis", "defeat", "loss", "criticism", "controversy"
    ]
    positive_words = [
        "fit", "returns", "victory", "win", "confident", "boost", "recovered",
        "returns to squad", "key player back", "optimistic", "praise"
    ]

    neg_score = sum(1 for word in negative_words if word in text_lower)
    pos_score = sum(1 for word in positive_words if word in text_lower)

    if neg_score > pos_score:
        return "negative"
    elif pos_score > neg_score:
        return "positive"
    return "neutral"


def fetch_espn_news_feed() -> list[dict]:
    """Parse RSS news feed from ESPN Soccer."""
    news_items = []
    try:
        req = urllib.request.Request(ESPN_RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root_el = ET.fromstring(xml_data)

            for item in root_el.findall(".//item"):
                title = item.find("title")
                desc = item.find("description")
                link = item.find("link")

                title_text = title.text if title is not None else ""
                desc_text = desc.text if desc is not None else ""
                link_text = link.text if link is not None else ""

                news_items.append({
                    "headline": title_text,
                    "detail": desc_text,
                    "url": link_text
                })
    except Exception as e:
        print(f"Warning: ESPN RSS news feed parse failed ({e}). Generating mock news.", file=sys.stderr)

    return news_items


def get_mock_news_for_teams(teams: list[tuple[str, str]]) -> list[dict]:
    """Generate realistic mock news for testing news flow."""
    mock_news = []
    for team_id, team_name in teams:
        # Generates a mix of positive and negative mock headlines
        if len(team_name) % 2 == 0:
            mock_news.append({
                "headline": f"{team_name} key midfielder returns to training ahead of crucial clash",
                "detail": f"Good news for the coach as the squad receives a boost with players recovering from minor knocks.",
                "sentiment": "positive",
                "team_code": team_id,
                "source": "mock_espn"
            })
        else:
            mock_news.append({
                "headline": f"Injury blow for {team_name} as star forward is ruled out",
                "detail": f"The medical team confirmed that the player will miss the upcoming match due to a muscle strain.",
                "sentiment": "negative",
                "team_code": team_id,
                "source": "mock_espn"
            })
    return mock_news


def update_news_in_evidence(*, root: Path, edition: str, date_str: str) -> dict:
    ledger = load_match_ledger(root, edition)
    matches_on_day = [m for m in ledger.get("matches", []) if match_on_date(m, date_str)]

    if not matches_on_day:
        return {"status": "no_matches_on_date", "date": date_str}

    # Extract all playing teams for this date
    teams = []
    for match in matches_on_day:
        teams.append((match["home_team"]["team_id"], match["home_team"]["name"]))
        teams.append((match["away_team"]["team_id"], match["away_team"]["name"]))

    # Fetch sports news from ESPN RSS
    fetched_news = fetch_espn_news_feed()
    relevant_news = []

    # Map articles to teams and analyze sentiment
    for item in fetched_news:
        headline = item["headline"]
        detail = item["detail"]

        # Check if any team name matches
        for team_id, team_name in teams:
            if team_name.lower() in headline.lower() or team_name.lower() in detail.lower():
                relevant_news.append({
                    "headline": headline,
                    "detail": detail,
                    "sentiment": analyze_sentiment(headline + " " + detail),
                    "team_code": team_id,
                    "source": "espn_rss",
                    "source_url": item["url"]
                })

    # If no actual news is found, generate mock news as fallback to test the pipeline
    if not relevant_news:
        relevant_news = get_mock_news_for_teams(teams)

    # Load daily evidence
    evidence_dir = edition_data_root(root, edition) / "daily-evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / f"{date_str}.json"

    evidence = load_json(evidence_path, default={})
    if not evidence:
        evidence = {
            "version": 1,
            "edition": edition,
            "date": date_str,
            "generated_at": iso_now(),
            "mode": "daily-evidence",
            "status": "empty",
            "matches": [],
            "injuries": [],
            "suspensions": [],
            "probable_lineups": [],
            "late_news": [],
            "source_refs": [],
        }

    # Append new late news to daily evidence, avoiding duplicates
    existing_headlines = {n["headline"] for n in evidence.setdefault("late_news", [])}
    added_count = 0
    for news_item in relevant_news:
        if news_item["headline"] not in existing_headlines:
            # Format to store in late_news
            evidence["late_news"].append({
                "headline": news_item["headline"],
                "detail": news_item.get("detail", ""),
                "sentiment": news_item.get("sentiment", "neutral"),
                "team_code": news_item["team_code"],
                "source": news_item["source"],
                "recorded_at": iso_now()
            })
            added_count += 1

    evidence["generated_at"] = iso_now()
    evidence["status"] = "updated"

    # Add RSS source reference
    evidence.setdefault("source_refs", []).append({
        "source": "espn_rss_feed",
        "url": ESPN_RSS_URL,
        "recorded_at": iso_now()
    })

    write_json(evidence_path, evidence)
    return {
        "status": "news_updated",
        "date": date_str,
        "added_count": added_count,
        "total_news_count": len(evidence["late_news"])
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_odds = sub.add_parser("fetch-odds", help="Fetch betting odds for World Cup matches")
    fetch_odds.add_argument("--edition", required=True)
    fetch_odds.add_argument("--date", required=True)
    fetch_odds.add_argument("--root", default=".")

    fetch_news = sub.add_parser("fetch-news", help="Fetch sports news sentiment for World Cup matches")
    fetch_news.add_argument("--edition", required=True)
    fetch_news.add_argument("--date", required=True)
    fetch_news.add_argument("--root", default=".")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    edition = args.edition
    date_str = args.date

    if args.command == "fetch-odds":
        api_key = os.environ.get("THE_ODDS_API_KEY")
        res = update_odds_in_evidence(root=root, edition=edition, date_str=date_str, api_key=api_key)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.command == "fetch-news":
        res = update_news_in_evidence(root=root, edition=edition, date_str=date_str)
        print(json.dumps(res, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
