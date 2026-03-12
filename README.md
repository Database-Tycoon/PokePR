# PokéPR

A GitHub Action that turns every pull request into a Pokémon encounter.

Open a PR — a wild Pokémon appears. Merge it — you catch it. Close it without merging — it flees.

The Pokémon is determined by the PR number: PR #1 encounters Bulbasaur, PR #4 encounters Charmander, PR #25 encounters Pikachu, and so on through the entire Pokédex.

---

## Quick Start

Copy the workflow file into your repository and you are done.

1. Create `.github/workflows/pokepr.yml` in your repository with this content:

```yaml
name: PokéPR

on:
  pull_request:
    types: [opened, reopened, closed]

jobs:
  pokepr:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: Database-Tycoon/PokePR@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

2. Open a pull request. That's it.

The action posts a comment automatically on every PR open, reopen, and close event.

---

## Pokédex Tracking (Optional)

You can track which Pokémon you have seen and caught across all your PRs using a GitHub Gist. The Gist will contain a `pokedex.json` file and a `POKEDEX.md` table you can share.

Once configured, every PR comment will include a **View Pokédex** link pointing directly to your Gist, and the action will automatically update it as you encounter, catch, and miss Pokémon.

### Setup via GitHub CLI

Most of this can be done entirely from the terminal with `gh`.

**Step 1 — Create the Gist**

```bash
gh gist create --desc "My PokéPR Pokédex" --public
```

Note the Gist ID from the URL it prints — it's the hash at the end.

**Step 2 — Create a Personal Access Token**

This is the one step that requires the browser. Go to:

> GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)

Generate a new token with only the `gist` scope selected.

**Step 3 — Add both secrets to your repository**

```bash
gh secret set POKEDEX_GIST_ID --body "your-gist-id-here" --repo owner/repo
gh secret set POKEDEX_GIST_TOKEN --body "your-token-here" --repo owner/repo
```

**Step 4 — Update your workflow**

```yaml
- uses: Database-Tycoon/PokePR@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    gist-id: ${{ secrets.POKEDEX_GIST_ID }}
    gist-token: ${{ secrets.POKEDEX_GIST_TOKEN }}
```

### Setup via GitHub web UI

**Step 1 — Create a Gist**

Go to [gist.github.com](https://gist.github.com) and create a new public or secret Gist. Give it any filename — PokéPR will add its own files. Note the Gist ID from the URL:

```
https://gist.github.com/yourusername/THIS_PART_IS_THE_ID
```

**Step 2 — Create a Personal Access Token**

Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic). Generate a new token with only the `gist` scope selected.

**Step 3 — Add secrets to your repository**

In your repository settings under Secrets and variables → Actions, add two secrets:

- `POKEDEX_GIST_ID` — the Gist ID from step 1
- `POKEDEX_GIST_TOKEN` — the token from step 2

**Step 4 — Update your workflow** (same as above)

---

## How It Works

- **PR opened or reopened**: PokéPR fetches the Pokémon matching your PR number from [PokeAPI](https://pokeapi.co) and posts a comment with its sprite, type, and Pokédex entry. If a Gist is configured, the Pokémon is marked as **seen**.

- **PR merged**: The existing comment is updated to a catch celebration. If a Gist is configured, the Pokémon is promoted to **caught** and removed from the seen list.

- **PR closed without merging**: The comment is updated to show the Pokémon fleeing. It stays marked as **seen** in your Pokédex if it was there.

PokéPR uses a hidden HTML comment marker inside each comment body (`<!-- pokepr-marker -->`) to find and update its own comments rather than posting duplicates.

---

## Pokédex Number Reference

| PR # | Pokémon |
|------|---------|
| 1 | Bulbasaur |
| 4 | Charmander |
| 7 | Squirtle |
| 25 | Pikachu |
| 39 | Jigglypuff |
| 152 | Chikorita |
| 155 | Cyndaquil |

Pokémon are mapped by their official National Pokédex number. PokeAPI supports entries up to #1025 (as of Generation IX), so even very high-numbered PRs will encounter a Pokémon.

---

## Installing as a Python Package

PokéPR can also be installed as a regular Python package and run from the command line or imported into your own scripts.

```bash
pip install pokepr
```

Run it by setting the environment variables manually:

```bash
export GITHUB_TOKEN="ghp_..."
export GITHUB_REPOSITORY="owner/repo"
export PR_NUMBER="4"
export PR_ACTION="opened"
python -m pokepr
```

---

## License

MIT




