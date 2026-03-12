"""
Entry point for PokéPR GitHub Action.

Reads environment variables set by the action runner and orchestrates
Pokémon encounters, catches, and escapes on GitHub PRs.
"""

import os
import sys
from typing import Optional


def _get_env(name: str, required: bool = True) -> str:
    """Read an environment variable, raising on missing required vars."""
    value = os.environ.get(name, "").strip()
    if required and not value:
        raise EnvironmentError(
            f"Required environment variable {name!r} is not set or empty."
        )
    return value


def main() -> None:
    # --- Read environment variables ---
    try:
        github_token = _get_env("GITHUB_TOKEN")
        repo = _get_env("GITHUB_REPOSITORY")
        pr_number_str = _get_env("PR_NUMBER")
        pr_action = _get_env("PR_ACTION")
    except EnvironmentError as exc:
        print(f"[pokepr] Configuration error: {exc}")
        sys.exit(0)

    try:
        pr_number = int(pr_number_str)
    except ValueError:
        print(f"[pokepr] Invalid PR_NUMBER: {pr_number_str!r} — must be an integer.")
        sys.exit(0)

    pr_merged = _get_env("PR_MERGED", required=False).lower() == "true"
    gist_id = _get_env("GIST_ID", required=False)
    gist_token = _get_env("GIST_TOKEN", required=False)

    # Gist is only usable if both ID and token are provided
    gist_configured = bool(gist_id and gist_token)

    # --- Import modules here so any import errors are caught gracefully ---
    try:
        from pokepr.pokemon import get_pokemon
        from pokepr.pr_comment import (
            post_or_update_comment,
            build_encounter_comment,
            build_caught_comment,
            build_fled_comment,
        )
        from pokepr.gist import load_pokedex, update_pokedex
    except Exception as exc:
        print(f"[pokepr] Failed to import modules: {exc}")
        sys.exit(0)

    # --- No-op for actions we don't handle ---
    if pr_action not in ("opened", "reopened", "closed"):
        print(f"[pokepr] Action {pr_action!r} is not handled — skipping.")
        sys.exit(0)

    # --- Fetch Pokémon ---
    try:
        pokemon = get_pokemon(pr_number)
        print(f"[pokepr] Fetched Pokémon #{pokemon.number}: {pokemon.name} ({', '.join(pokemon.types)})")
    except Exception as exc:
        print(f"[pokepr] Could not fetch Pokémon for PR #{pr_number}: {exc}")
        sys.exit(0)

    # --- Resolve Gist URL for footer links ---
    gist_html_url: Optional[str] = None
    if gist_configured:
        try:
            _, gist_html_url = load_pokedex(gist_id, gist_token)
        except Exception as exc:
            print(f"[pokepr] Warning: could not load Pokédex gist — {exc}")
            gist_html_url = None

    # --- Handle each PR action ---
    try:
        if pr_action in ("opened", "reopened"):
            body = build_encounter_comment(pokemon, gist_html_url)
            post_or_update_comment(github_token, repo, pr_number, body)
            print(f"[pokepr] Posted encounter comment for {pokemon.name} on PR #{pr_number}.")

            if gist_configured:
                try:
                    update_pokedex(gist_id, gist_token, pokemon, "seen")
                    print(f"[pokepr] Marked {pokemon.name} as seen in Pokédex.")
                except Exception as exc:
                    print(f"[pokepr] Warning: could not update Pokédex — {exc}")

        elif pr_action == "closed":
            if pr_merged:
                body = build_caught_comment(pokemon, gist_html_url)
                post_or_update_comment(github_token, repo, pr_number, body)
                print(f"[pokepr] Updated comment — {pokemon.name} was caught!")

                if gist_configured:
                    try:
                        update_pokedex(gist_id, gist_token, pokemon, "caught")
                        print(f"[pokepr] Marked {pokemon.name} as caught in Pokédex.")
                    except Exception as exc:
                        print(f"[pokepr] Warning: could not update Pokédex — {exc}")
            else:
                body = build_fled_comment(pokemon, gist_html_url)
                post_or_update_comment(github_token, repo, pr_number, body)
                print(f"[pokepr] Updated comment — {pokemon.name} fled!")
                # Already marked as "seen" when the PR was opened — no further update needed.

    except Exception as exc:
        print(f"[pokepr] Failed to post/update PR comment: {exc}")
        sys.exit(0)


if __name__ == "__main__":
    main()
