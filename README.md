# Product Branding

Claude Code plugin for naming software products and checking availability
across domains, GitHub orgs, and package registries.

## Install

Requires the [productivity marketplace](https://github.com/krisrowe/claude-plugins):

```bash
claude plugin marketplace add https://github.com/krisrowe/claude-plugins.git
claude plugin marketplace update claude-plugins
claude plugin install product-branding@claude-plugins --scope user
```

## Usage

The plugin activates automatically when you ask about naming a product:

```
> I need a name for a CLI tool that manages cloud deployments
> What should I call my new Python testing framework?
> Check if "vortex" is available as a product name
```

Or invoke explicitly:

```
/product-branding:product-branding my deployment CLI tool
```

## What it does

**Brainstorms names** — the skill generates candidates across styles
(descriptive, metaphorical, short/punchy, abstract) informed by your saved
keywords and naming guidelines.

**Checks availability** — domains (.com, .dev, .io, .ai), GitHub orgs,
PyPI, npm, crates.io, Docker Hub, Homebrew. Batch sweep or targeted
follow-ups.

**Saves and annotates candidates** — brand names persist across sessions
with three-state availability tracking (available / unavailable / unknown /
unchecked), free-form tags, notes, and timestamped comments. Filter saved
brands by tag, availability status, or name search.

**Remembers your preferences** — which services and domain tiers matter,
brainstorming keywords, and naming guidelines carry over between sessions.

## Example session

```
User: "I need a name for my MCP framework ecosystem"

→ Agent loads preferences and saved brands from prior sessions
→ Brainstorms 10 candidates
→ Batch checks all 10 across domains, GitHub, PyPI
→ Presents comparison table with ✅/❌ per namespace
→ User picks favorites, agent saves with availability + tags

User: "What about the .ai domain for echoark?"

→ Single targeted domain check, result in seconds

User: "Save echoark as a finalist for dev-tools"

→ add_brand with tags and notes, persisted for next session
```

## Tools

See [TOOLS.md](TOOLS.md) for the complete tool interface reference.

**Availability checks:**
`check_name_availability` (batch orchestrator),
`check_domain`, `check_github_org`, `check_pypi`, `check_npm`,
`check_crates`, `check_docker_hub`, `check_homebrew`

**Brand management:**
`add_brand`, `update_brand`, `update_brand_availability`,
`list_brands`, `remove_brand`

**Preferences:**
`brand_search_preferences`

## Preferences

Stored at `~/.config/product-branding/preferences.json` (respects
`$XDG_CONFIG_HOME`). Persists across sessions and plugin updates.

- **Services** — which availability checks to run
- **Domain tiers** — which extensions are critical, nice-to-have, or ignorable
- **Keywords** — brainstorming inspiration words
- **Guidelines** — naming rules in your own words
- **Liked brands** — rich objects with availability, tags, notes, and comments

## Prerequisites

- `gh` CLI (for GitHub org checks)
- `whois` (for domain checks)
- `brew` (for Homebrew checks, optional — degrades gracefully if missing)
