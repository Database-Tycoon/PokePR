"""
PokeAPI integration for fetching Pokémon data by PR number.
"""

from dataclasses import dataclass
import requests


POKEAPI_BASE = "https://pokeapi.co/api/v2"
REQUEST_TIMEOUT = 10

# Emoji representation of each type for use in comments
TYPE_EMOJI: dict[str, str] = {
    "normal":   "⚪ Normal",
    "fire":     "🔥 Fire",
    "water":    "💧 Water",
    "electric": "⚡ Electric",
    "grass":    "🌿 Grass",
    "ice":      "🧊 Ice",
    "fighting": "🥊 Fighting",
    "poison":   "☠️ Poison",
    "ground":   "🏔️ Ground",
    "flying":   "🌬️ Flying",
    "psychic":  "🔮 Psychic",
    "bug":      "🐛 Bug",
    "rock":     "🪨 Rock",
    "ghost":    "👻 Ghost",
    "dragon":   "🐉 Dragon",
    "dark":     "🌑 Dark",
    "steel":    "⚙️ Steel",
    "fairy":    "🌸 Fairy",
}


@dataclass
class Ability:
    name: str
    is_hidden: bool


@dataclass
class Pokemon:
    number: int
    name: str
    genus: str              # e.g. "Tiny Turtle Pokémon"
    types: list[str]        # lowercase, e.g. ["water"]
    flavor_text: str
    height_m: float
    weight_kg: float
    sprite_url: str
    abilities: list[Ability]
    base_stats: dict[str, int]  # e.g. {"hp": 44, "attack": 48, ...}


def _clean_flavor_text(text: str) -> str:
    cleaned = text.replace("\f", " ").replace("\n", " ")
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return cleaned.strip()


def get_pokemon(pr_number: int) -> Pokemon:
    """
    Fetch Pokémon data from PokeAPI for the given PR number.

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

    # Types (ordered by slot, stored lowercase for emoji lookup)
    types = [
        entry["type"]["name"].lower()
        for entry in sorted(pokemon_data["types"], key=lambda e: e["slot"])
    ]

    # First English flavor text
    flavor_text = ""
    for entry in species_data.get("flavor_text_entries", []):
        if entry["language"]["name"] == "en":
            flavor_text = _clean_flavor_text(entry["flavor_text"])
            break

    # Height (decimetres → metres) and weight (hectograms → kilograms)
    height_m = pokemon_data["height"] / 10
    weight_kg = pokemon_data["weight"] / 10

    # Official artwork sprite
    sprite_url = (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/"
        f"sprites/pokemon/other/official-artwork/{pr_number}.png"
    )

    # Abilities (sorted by slot, flag hidden ones)
    abilities = [
        Ability(
            name=entry["ability"]["name"].replace("-", " ").title(),
            is_hidden=entry["is_hidden"],
        )
        for entry in sorted(pokemon_data["abilities"], key=lambda e: e["slot"])
    ]

    # Base stats — use the canonical short names
    stat_name_map = {
        "hp":              "HP",
        "attack":          "Attack",
        "defense":         "Defense",
        "special-attack":  "Sp. Atk",
        "special-defense": "Sp. Def",
        "speed":           "Speed",
    }
    base_stats: dict[str, int] = {}
    for entry in pokemon_data["stats"]:
        key = entry["stat"]["name"]
        if key in stat_name_map:
            base_stats[stat_name_map[key]] = entry["base_stat"]

    return Pokemon(
        number=pr_number,
        name=name,
        genus=genus,
        types=types,
        flavor_text=flavor_text,
        height_m=height_m,
        weight_kg=weight_kg,
        sprite_url=sprite_url,
        abilities=abilities,
        base_stats=base_stats,
    )
