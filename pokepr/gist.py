"""
GitHub Gist Pokédex tracking — stores caught/seen Pokémon as JSON and markdown.
"""

import copy
import json
import requests
from datetime import datetime, timezone
from typing import Any

from pokepr.pokemon import Pokemon, TYPE_EMOJI


REQUEST_TIMEOUT = 10
GIST_API_BASE = "https://api.github.com/gists"
POKEDEX_JSON_FILENAME = "pokedex.json"
POKEDEX_MD_FILENAME = "POKEDEX.md"

EMPTY_POKEDEX: dict[str, list[dict[str, Any]]] = {"caught": [], "seen": []}


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_dt(iso: str) -> str:
    """Format an ISO timestamp as a readable date, e.g. 'Mar 12 2026'."""
    try:
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %-d %Y")
    except Exception:
        return iso


def load_pokedex(gist_id: str, token: str) -> tuple[dict[str, Any], str]:
    """
    Load the Pokédex data from a GitHub Gist.

    Returns:
        A tuple of (pokedex_data, gist_html_url).
    """
    resp = requests.get(
        f"{GIST_API_BASE}/{gist_id}",
        headers=_auth_headers(token),
        timeout=REQUEST_TIMEOUT,
    )
    if not resp.ok:
        raise ValueError(
            f"Failed to fetch gist {gist_id}: HTTP {resp.status_code} — {resp.text}"
        )

    gist_data = resp.json()
    gist_html_url: str = gist_data.get("html_url", f"https://gist.github.com/{gist_id}")

    files = gist_data.get("files", {})
    if POKEDEX_JSON_FILENAME not in files:
        return copy.deepcopy(EMPTY_POKEDEX), gist_html_url

    raw_url = files[POKEDEX_JSON_FILENAME].get("raw_url", "")
    if not raw_url:
        return copy.deepcopy(EMPTY_POKEDEX), gist_html_url

    raw_resp = requests.get(raw_url, timeout=REQUEST_TIMEOUT)
    if not raw_resp.ok:
        return copy.deepcopy(EMPTY_POKEDEX), gist_html_url

    try:
        pokedex = raw_resp.json()
    except json.JSONDecodeError:
        pokedex = copy.deepcopy(EMPTY_POKEDEX)

    pokedex.setdefault("caught", [])
    pokedex.setdefault("seen", [])

    return pokedex, gist_html_url


def _build_pokedex_md(pokedex: dict[str, Any], gist_html_url: str) -> str:
    caught = pokedex.get("caught", [])
    seen = pokedex.get("seen", [])

    caught_count = len(caught)
    seen_count = len(seen)

    def _pr_link(entry: dict, key_url: str, key_at: str) -> str:
        url = entry.get(key_url, "")
        at = entry.get(key_at, "")
        if url and at:
            return f"[{_format_dt(at)}]({url})"
        elif url:
            return f"[link]({url})"
        return "—"

    lines: list[str] = [
        "# 📖 My PokéPR Pokédex",
        "",
        f"**Caught**: {caught_count} | "
        f"**Seen**: {seen_count} (not caught) | "
        f"*Powered by [PokéPR](https://github.com/Database-Tycoon/PokePR)*",
        "",
        f"## ✅ Caught ({caught_count})",
        "",
        "| # | Name | Type | First Seen | Caught |",
        "|---|------|------|------------|--------|",
    ]

    for entry in caught:
        num = entry.get("number", 0)
        name = entry.get("name", "Unknown")
        types = entry.get("types", [])
        type_str = " / ".join(TYPE_EMOJI.get(t, t.title()) for t in types)
        seen_link = _pr_link(entry, "seen_pr", "seen_at")
        caught_link = _pr_link(entry, "caught_pr", "caught_at")
        lines.append(f"| {num:03d} | {name} | {type_str} | {seen_link} | {caught_link} |")

    if not caught:
        lines.append("| — | *None yet* | — | — | — |")

    lines += [
        "",
        f"## 👀 Seen ({seen_count})",
        "",
        "| # | Name | Type | First Seen |",
        "|---|------|------|------------|",
    ]

    for entry in seen:
        num = entry.get("number", 0)
        name = entry.get("name", "Unknown")
        types = entry.get("types", [])
        type_str = " / ".join(TYPE_EMOJI.get(t, t.title()) for t in types)
        seen_link = _pr_link(entry, "seen_pr", "seen_at")
        lines.append(f"| {num:03d} | {name} | {type_str} | {seen_link} |")

    if not seen:
        lines.append("| — | *None yet* | — | — |")

    return "\n".join(lines) + "\n"


def update_pokedex(
    gist_id: str,
    token: str,
    pokemon: Pokemon,
    status: str,
    pr_url: str = "",
    timestamp: str = "",
) -> None:
    """
    Update the Pokédex in the GitHub Gist with the given Pokémon and status.

    Args:
        gist_id: The ID of the GitHub Gist.
        token: A GitHub token with gist scope.
        pokemon: The Pokémon to add or update.
        status: Either "caught" or "seen".
        pr_url: URL of the PR where the event occurred.
        timestamp: ISO 8601 UTC timestamp of the event.
    """
    if status not in ("caught", "seen"):
        raise ValueError(f"status must be 'caught' or 'seen', got {status!r}")

    if not timestamp:
        timestamp = _now_utc()

    pokedex, gist_html_url = load_pokedex(gist_id, token)

    caught: list[dict[str, Any]] = pokedex["caught"]
    seen: list[dict[str, Any]] = pokedex["seen"]

    existing_caught = next((e for e in caught if e["number"] == pokemon.number), None)
    existing_seen = next((e for e in seen if e["number"] == pokemon.number), None)

    if status == "caught":
        if existing_caught:
            # Already caught — just update caught timestamp/PR if missing
            if not existing_caught.get("caught_at"):
                existing_caught["caught_at"] = timestamp
                existing_caught["caught_pr"] = pr_url
        else:
            entry: dict[str, Any] = {
                "number": pokemon.number,
                "name": pokemon.name,
                "types": pokemon.types,
                "caught_at": timestamp,
                "caught_pr": pr_url,
            }
            # Carry over seen metadata if we have it
            if existing_seen:
                entry["seen_at"] = existing_seen.get("seen_at", "")
                entry["seen_pr"] = existing_seen.get("seen_pr", "")
            caught.append(entry)

        # Remove from seen
        seen = [e for e in seen if e["number"] != pokemon.number]

    elif status == "seen":
        if existing_caught:
            return  # Do not downgrade
        if not existing_seen:
            seen.append({
                "number": pokemon.number,
                "name": pokemon.name,
                "types": pokemon.types,
                "seen_at": timestamp,
                "seen_pr": pr_url,
            })

    caught.sort(key=lambda e: e["number"])
    seen.sort(key=lambda e: e["number"])

    pokedex["caught"] = caught
    pokedex["seen"] = seen

    pokedex_json_content = json.dumps(pokedex, indent=2, ensure_ascii=False) + "\n"
    pokedex_md_content = _build_pokedex_md(pokedex, gist_html_url)

    payload = {
        "files": {
            POKEDEX_JSON_FILENAME: {"content": pokedex_json_content},
            POKEDEX_MD_FILENAME: {"content": pokedex_md_content},
        }
    }

    resp = requests.patch(
        f"{GIST_API_BASE}/{gist_id}",
        headers=_auth_headers(token),
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    if not resp.ok:
        raise ValueError(
            f"Failed to update gist {gist_id}: HTTP {resp.status_code} — {resp.text}"
        )
