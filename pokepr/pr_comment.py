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
    """
    Search the PR's comments for an existing PokéPR comment.

    Args:
        token: GitHub token.
        repo: Repository in "owner/repo" format.
        pr_number: The pull request number.

    Returns:
        The comment ID if found, otherwise None.
    """
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

        # If we got fewer than 100 results, we've seen all pages
        if len(comments) < 100:
            break
        page += 1

    return None


def post_comment(token: str, repo: str, pr_number: int, body: str) -> int:
    """
    Post a new comment on the PR.

    Args:
        token: GitHub token.
        repo: Repository in "owner/repo" format.
        pr_number: The pull request number.
        body: The markdown body of the comment.

    Returns:
        The ID of the newly created comment.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.post(
        url,
        headers=_auth_headers(token),
        json={"body": body},
        timeout=REQUEST_TIMEOUT,
    )
    if not resp.ok:
        raise ValueError(
            f"Failed to post comment on PR #{pr_number}: "
            f"HTTP {resp.status_code} — {resp.text}"
        )
    return resp.json()["id"]


def update_comment(token: str, repo: str, comment_id: int, body: str) -> None:
    """
    Update an existing comment by ID.

    Args:
        token: GitHub token.
        repo: Repository in "owner/repo" format.
        comment_id: The ID of the comment to update.
        body: The new markdown body.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/comments/{comment_id}"
    resp = requests.patch(
        url,
        headers=_auth_headers(token),
        json={"body": body},
        timeout=REQUEST_TIMEOUT,
    )
    if not resp.ok:
        raise ValueError(
            f"Failed to update comment {comment_id}: "
            f"HTTP {resp.status_code} — {resp.text}"
        )


def post_or_update_comment(
    token: str, repo: str, pr_number: int, body: str
) -> None:
    """
    Find the existing PokéPR comment and update it, or post a new one.

    Args:
        token: GitHub token.
        repo: Repository in "owner/repo" format.
        pr_number: The pull request number.
        body: The markdown body to post or update with.
    """
    comment_id = find_pokepr_comment(token, repo, pr_number)
    if comment_id is not None:
        update_comment(token, repo, comment_id, body)
    else:
        post_comment(token, repo, pr_number, body)


def _pokedex_footer(gist_html_url: Optional[str]) -> str:
    """Build the footer line, optionally including a Pokédex link."""
    powered_by = "*Powered by [pokepr](https://github.com/Database-Tycoon/PokePR)*"
    if gist_html_url:
        view_dex = f"*[📖 View Pokédex]({gist_html_url})*"
        return f"{view_dex} &nbsp;|&nbsp; {powered_by}"
    return powered_by


def build_encounter_comment(
    pokemon: Pokemon, gist_html_url: Optional[str] = None
) -> str:
    """
    Build the 'wild Pokémon appeared' comment body for an opened/reopened PR.

    Args:
        pokemon: The Pokémon for this PR.
        gist_html_url: Optional URL to the Pokédex Gist.

    Returns:
        Markdown string with the MARKER at the top.
    """
    type_str = " / ".join(pokemon.types)
    footer = _pokedex_footer(gist_html_url)

    lines = [
        MARKER,
        "## ⚔️ A wild Pokémon appeared!",
        "",
        f"![{pokemon.name}]({pokemon.sprite_url})",
        "",
        f"**A wild {pokemon.name} appeared!**",
        "",
        f"> *{pokemon.flavor_text}*",
        "",
        "| | |",
        "|---|---|",
        f"| **Pokédex #** | {pokemon.number:03d} |",
        f"| **Type** | {type_str} |",
        "",
        "---",
        f"*🎮 Merge this PR to catch **{pokemon.name}**! "
        f"Close it without merging and it will flee...*",
        "",
        footer,
    ]
    return "\n".join(lines)


def build_caught_comment(
    pokemon: Pokemon, gist_html_url: Optional[str] = None
) -> str:
    """
    Build the 'Gotcha! Pokémon was caught!' comment body for a merged PR.

    Args:
        pokemon: The Pokémon for this PR.
        gist_html_url: Optional URL to the Pokédex Gist.

    Returns:
        Markdown string with the MARKER at the top.
    """
    type_str = " / ".join(pokemon.types)
    footer = _pokedex_footer(gist_html_url)

    lines = [
        MARKER,
        f"## 🎉 Gotcha! {pokemon.name} was caught!",
        "",
        f"![{pokemon.name}]({pokemon.sprite_url})",
        "",
        f"**{pokemon.name}** has been added to your Pokédex! 🔴",
        "",
        f"> *{pokemon.flavor_text}*",
        "",
        "| | |",
        "|---|---|",
        f"| **Pokédex #** | {pokemon.number:03d} |",
        f"| **Type** | {type_str} |",
        "",
        "---",
        footer,
    ]
    return "\n".join(lines)


def build_fled_comment(
    pokemon: Pokemon, gist_html_url: Optional[str] = None
) -> str:
    """
    Build the 'Pokémon fled!' comment body for a closed-without-merge PR.

    Args:
        pokemon: The Pokémon for this PR.
        gist_html_url: Optional URL to the Pokédex Gist.

    Returns:
        Markdown string with the MARKER at the top.
    """
    type_str = " / ".join(pokemon.types)
    footer = _pokedex_footer(gist_html_url)

    lines = [
        MARKER,
        f"## 💨 {pokemon.name} fled!",
        "",
        f"![{pokemon.name}]({pokemon.sprite_url})",
        "",
        f"**{pokemon.name}** broke free and escaped! "
        f"It has been marked as **seen** in your Pokédex.",
        "",
        f"> *{pokemon.flavor_text}*",
        "",
        "| | |",
        "|---|---|",
        f"| **Pokédex #** | {pokemon.number:03d} |",
        f"| **Type** | {type_str} |",
        "",
        "---",
        footer,
    ]
    return "\n".join(lines)
