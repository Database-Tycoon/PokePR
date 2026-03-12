"""
PokeAPI integration for fetching Pokémon data by PR number.
"""

from dataclasses import dataclass
import requests


POKEAPI_BASE = "https://pokeapi.co/api/v2"
REQUEST_TIMEOUT = 10


@dataclass
class Pokemon:
    number: int
    name: str
    types: list[str]
    flavor_text: str
    sprite_url: str


def _clean_flavor_text(text: str) -> str:
    """Replace form-feed and newline characters with spaces, collapse runs."""
    cleaned = text.replace("\f", " ").replace("\n", " ")
    # Collapse multiple spaces into one
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return cleaned.strip()


def get_pokemon(pr_number: int) -> Pokemon:
    """
    Fetch Pokémon data from PokeAPI for the given PR number.

    Args:
        pr_number: The pull request number, used as the Pokédex number.

    Returns:
        A Pokemon dataclass with name, types, flavor text, and sprite URL.

    Raises:
        ValueError: If the PR number is out of the known Pokédex range or API fails.
        requests.RequestException: On network errors.
    """
    pokemon_url = f"{POKEAPI_BASE}/pokemon/{pr_number}"
    species_url = f"{POKEAPI_BASE}/pokemon-species/{pr_number}"

    # Fetch main pokemon data
    pokemon_resp = requests.get(pokemon_url, timeout=REQUEST_TIMEOUT)
    if not pokemon_resp.ok:
        raise ValueError(
            f"PokeAPI returned {pokemon_resp.status_code} for Pokémon #{pr_number}. "
            f"The Pokédex only goes up to #1025 (as of this writing)."
        )
    pokemon_data = pokemon_resp.json()

    # Fetch species data for flavor text
    species_resp = requests.get(species_url, timeout=REQUEST_TIMEOUT)
    if not species_resp.ok:
        raise ValueError(
            f"PokeAPI returned {species_resp.status_code} for species #{pr_number}."
        )
    species_data = species_resp.json()

    # Extract name (title-case the API's lowercase name)
    name = pokemon_data["name"].replace("-", " ").title()

    # Extract types
    types = [
        entry["type"]["name"].title()
        for entry in sorted(pokemon_data["types"], key=lambda e: e["slot"])
    ]

    # Extract first English flavor text
    flavor_text = ""
    for entry in species_data.get("flavor_text_entries", []):
        if entry["language"]["name"] == "en":
            flavor_text = _clean_flavor_text(entry["flavor_text"])
            break

    # Extract sprite — prefer front_default, fall back to official artwork
    sprites = pokemon_data.get("sprites", {})
    sprite_url: str = sprites.get("front_default") or ""
    if not sprite_url:
        other = sprites.get("other", {})
        artwork = other.get("official-artwork", {})
        sprite_url = artwork.get("front_default") or ""

    # Use the raw GitHub sprite URL for reliable GitHub markdown rendering
    github_sprite_url = (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/"
        f"sprites/pokemon/{pr_number}.png"
    )

    return Pokemon(
        number=pr_number,
        name=name,
        types=types,
        flavor_text=flavor_text,
        sprite_url=github_sprite_url,
    )
