"""
GitHub Gist Pokédex tracking — stores caught/seen Pokémon as JSON and markdown.
"""

import copy
import json
import requests
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


def load_pokedex(gist_id: str, token: str) -> tuple[dict[str, Any], str]:
    """
    Load the Pokédex data from a GitHub Gist.

    Args:
        gist_id: The ID of the GitHub Gist.
        token: A GitHub token with gist scope.

    Returns:
        A tuple of (pokedex_data, gist_html_url).
        pokedex_data has keys "caught" and "seen", each a list of dicts.
        If the pokedex.json file does not exist in the gist, returns an empty structure.

    Raises:
        requests.RequestException: On network errors.
        ValueError: If the gist cannot be fetched.
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
        pokedex = dict(EMPTY_POKEDEX)

    # Ensure expected keys exist
    pokedex.setdefault("caught", [])
    pokedex.setdefault("seen", [])

    return pokedex, gist_html_url


def _build_pokedex_md(pokedex: dict[str, Any], gist_html_url: str) -> str:
    """Generate the POKEDEX.md markdown content from the current Pokédex data."""
    caught = pokedex.get("caught", [])
    seen = pokedex.get("seen", [])

    caught_count = len(caught)
    seen_count = len(seen)

    lines: list[str] = [
        "# \U0001f4d6 My PokéPR Pokédex",
        "",
        f"**Caught**: {caught_count} | "
        f"**Seen**: {seen_count} (not caught) | "
        f"*Powered by [pokepr](https://github.com/Database-Tycoon/PokePR)*",
        "",
        f"## \u2705 Caught ({caught_count})",
        "",
        "| # | Name | Type |",
        "|---|------|------|",
    ]

    for entry in caught:
        num = entry.get("number", 0)
        name = entry.get("name", "Unknown")
        types = entry.get("types", [])
        type_str = " / ".join(TYPE_EMOJI.get(t, t.title()) for t in types)
        lines.append(f"| {num:03d} | {name} | {type_str} |")

    if not caught:
        lines.append("| — | *None yet* | — |")

    lines += [
        "",
        f"## \U0001f440 Seen ({seen_count})",
        "",
        "| # | Name | Type |",
        "|---|------|------|",
    ]

    for entry in seen:
        num = entry.get("number", 0)
        name = entry.get("name", "Unknown")
        types = entry.get("types", [])
        type_str = " / ".join(TYPE_EMOJI.get(t, t.title()) for t in types)
        lines.append(f"| {num:03d} | {name} | {type_str} |")

    if not seen:
        lines.append("| — | *None yet* | — |")

    return "\n".join(lines) + "\n"


def update_pokedex(gist_id: str, token: str, pokemon: Pokemon, status: str) -> None:
    """
    Update the Pokédex in the GitHub Gist with the given Pokémon and status.

    Args:
        gist_id: The ID of the GitHub Gist.
        token: A GitHub token with gist scope.
        pokemon: The Pokémon to add or update.
        status: Either "caught" or "seen".

    Rules:
        - If already caught, do not downgrade to seen.
        - If caught, remove from the seen list.
        - Both lists are sorted by Pokédex number after any update.

    Raises:
        requests.RequestException: On network errors.
        ValueError: If the gist cannot be fetched or updated.
    """
    if status not in ("caught", "seen"):
        raise ValueError(f"status must be 'caught' or 'seen', got {status!r}")

    pokedex, gist_html_url = load_pokedex(gist_id, token)

    caught: list[dict[str, Any]] = pokedex["caught"]
    seen: list[dict[str, Any]] = pokedex["seen"]

    pokemon_entry: dict[str, Any] = {
        "number": pokemon.number,
        "name": pokemon.name,
        "types": pokemon.types,
    }

    # Check if already in caught list
    already_caught = any(e["number"] == pokemon.number for e in caught)

    if status == "caught":
        if not already_caught:
            # Add to caught
            caught.append(pokemon_entry)
        # Remove from seen regardless (caught supersedes seen)
        seen = [e for e in seen if e["number"] != pokemon.number]

    elif status == "seen":
        if already_caught:
            # Do not downgrade from caught to seen
            return
        already_seen = any(e["number"] == pokemon.number for e in seen)
        if not already_seen:
            seen.append(pokemon_entry)

    # Sort both lists by number
    caught.sort(key=lambda e: e["number"])
    seen.sort(key=lambda e: e["number"])

    pokedex["caught"] = caught
    pokedex["seen"] = seen

    # Build updated file contents
    pokedex_json_content = json.dumps(pokedex, indent=2, ensure_ascii=False) + "\n"
    pokedex_md_content = _build_pokedex_md(pokedex, gist_html_url)

    # PATCH the gist
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
