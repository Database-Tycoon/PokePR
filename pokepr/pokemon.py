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
    genus: str        # e.g. "Tiny Turtle Pokémon"
    types: list[str]
    flavor_text: str
    height_m: float   # height in metres
    weight_kg: float  # weight in kilograms
    sprite_url: str


def _clean_flavor_text(text: str) -> str:
    """Replace form-feed and newline characters with spaces, collapse runs."""
    cleaned = text.replace("\f", " ").replace("\n", " ")
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return cleaned.strip()


def get_pokemon(pr_number: int) -> Pokemon:
    """
    Fetch Pokémon data from PokeAPI for the given PR number.

    Returns:
        A Pokemon dataclass populated from the PokeAPI pokemon and
        pokemon-species endpoints.

    Raises:
        ValueError: If the API returns an error for this number.
        requests.RequestException: On network errors.
    """
    pokemon_resp = requests.get(
        f"{POKEAPI_BASE}/pokemon/{pr_number}", timeout=REQUEST_TIMEOUT
    )
    if not pokemon_resp.ok:
        raise ValueError(
            f"PokeAPI returned {pokemon_resp.status_code} for Pokémon #{pr_number}."
        )
    pokemon_data = pokemon_resp.json()

    species_resp = requests.get(
        f"{POKEAPI_BASE}/pokemon-species/{pr_number}", timeout=REQUEST_TIMEOUT
    )
    if not species_resp.ok:
        raise ValueError(
            f"PokeAPI returned {species_resp.status_code} for species #{pr_number}."
        )
    species_data = species_resp.json()

    # Name
    name = pokemon_data["name"].replace("-", " ").title()

    # Genus — "Seed Pokémon", "Tiny Turtle Pokémon", etc.
    genus = ""
    for entry in species_data.get("genera", []):
        if entry["language"]["name"] == "en":
            genus = entry["genus"]
            break

    # Types (ordered by slot)
    types = [
        entry["type"]["name"].title()
        for entry in sorted(pokemon_data["types"], key=lambda e: e["slot"])
    ]

    # First English flavor text entry
    flavor_text = ""
    for entry in species_data.get("flavor_text_entries", []):
        if entry["language"]["name"] == "en":
            flavor_text = _clean_flavor_text(entry["flavor_text"])
            break

    # Height (decimetres → metres) and weight (hectograms → kilograms)
    height_m = pokemon_data["height"] / 10
    weight_kg = pokemon_data["weight"] / 10

    # Official artwork sprite — much higher quality than front_default
    sprite_url = (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/"
        f"sprites/pokemon/other/official-artwork/{pr_number}.png"
    )

    return Pokemon(
        number=pr_number,
        name=name,
        genus=genus,
        types=types,
        flavor_text=flavor_text,
        height_m=height_m,
        weight_kg=weight_kg,
        sprite_url=sprite_url,
    )
