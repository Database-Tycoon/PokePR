"""
GitHub PR comment management for posting and updating PokéPR comments.
"""

from typing import Optional
import requests

from pokepr.pokemon import Pokemon


REQUEST_TIMEOUT = 10
GITHUB_API_BASE = "https://api.github.com"
MARKER = "<!-- pokepr-marker -->"


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def find_pokepr_comment(token: str, repo: str, pr_number: int) -> Optional[int]:
    """Search PR comments for an existing PokéPR comment. Returns comment ID or None."""
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    page = 1

    while True:
        resp = requests.get(
            url,
            headers=_auth_headers(token),
            params={"per_page": 100, "page": page},
            timeout=REQUEST_TIMEOUT,
        )
        if not resp.ok:
            raise ValueError(
                f"Failed to list comments for PR #{pr_number}: "
                f"HTTP {resp.status_code} — {resp.text}"
            )

        comments = resp.json()
        if not comments:
            break
        for comment in comments:
            if MARKER in comment.get("body", ""):
                return comment["id"]
        if len(comments) < 100:
            break
        page += 1

    return None


def post_comment(token: str, repo: str, pr_number: int, body: str) -> int:
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.post(
        url, headers=_auth_headers(token), json={"body": body}, timeout=REQUEST_TIMEOUT
    )
    if not resp.ok:
        raise ValueError(
            f"Failed to post comment on PR #{pr_number}: "
            f"HTTP {resp.status_code} — {resp.text}"
        )
    return resp.json()["id"]


def update_comment(token: str, repo: str, comment_id: int, body: str) -> None:
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/comments/{comment_id}"
    resp = requests.patch(
        url, headers=_auth_headers(token), json={"body": body}, timeout=REQUEST_TIMEOUT
    )
    if not resp.ok:
        raise ValueError(
            f"Failed to update comment {comment_id}: "
            f"HTTP {resp.status_code} — {resp.text}"
        )


def post_or_update_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    """Find the existing PokéPR comment and update it, or post a new one."""
    comment_id = find_pokepr_comment(token, repo, pr_number)
    if comment_id is not None:
        update_comment(token, repo, comment_id, body)
    else:
        post_comment(token, repo, pr_number, body)


def _footer(gist_html_url: Optional[str]) -> str:
    powered_by = "*Powered by [PokéPR](https://github.com/Database-Tycoon/PokePR)*"
    if gist_html_url:
        return f"*[📖 View Pokédex]({gist_html_url})* &nbsp;|&nbsp; {powered_by}"
    return powered_by


def _pokedex_entry(pokemon: Pokemon, status_line: str, footer: str) -> str:
    """
    Shared Pokédex-entry layout used by all three comment states.

    The image is always rendered using an HTML <img> tag so it is guaranteed
    to appear even if GitHub's markdown renderer strips bare image syntax.
    """
    types_str = " · ".join(f"**{t}**" for t in pokemon.types)

    return f"""{MARKER}
<img align="right" src="{pokemon.sprite_url}" width="175" alt="{pokemon.name}"/>

### 🔴 &nbsp; Pokédex #{pokemon.number:03d}
## {pokemon.name}
##### The {pokemon.genus}

{types_str} &nbsp;·&nbsp; {pokemon.height_m:.1f} m &nbsp;·&nbsp; {pokemon.weight_kg:.1f} kg

> *{pokemon.flavor_text}*

---
{status_line}

{footer}"""


def build_encounter_comment(
    pokemon: Pokemon, gist_html_url: Optional[str] = None
) -> str:
    status = (
        f"⚔️ &nbsp; A wild **{pokemon.name}** appeared! "
        f"Merge this PR to catch it — close it and watch it flee."
    )
    return _pokedex_entry(pokemon, status, _footer(gist_html_url))


def build_caught_comment(
    pokemon: Pokemon, gist_html_url: Optional[str] = None
) -> str:
    status = f"✅ &nbsp; Gotcha! **{pokemon.name}** was caught and added to your Pokédex!"
    return _pokedex_entry(pokemon, status, _footer(gist_html_url))


def build_fled_comment(
    pokemon: Pokemon, gist_html_url: Optional[str] = None
) -> str:
    status = (
        f"💨 &nbsp; **{pokemon.name}** broke free and fled! "
        f"It has been marked as **seen** in your Pokédex."
    )
    return _pokedex_entry(pokemon, status, _footer(gist_html_url))
