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

## Tools

The plugin exposes MCP tools for availability checking:

### `check_name_availability`

Orchestrator — checks one or more names across all enabled services in parallel.
Returns a unified result respecting saved preferences.

```
check_name_availability(names=["vortex", "nexus", "forge"])
check_name_availability(names=["vortex"], services=["domain", "pypi"])
```

### Individual check tools

For targeted follow-ups when you already know which service to check:

- `check_domain(names, extensions)` — whois lookup for domain availability
- `check_github_org(names)` — GitHub org/user name availability
- `check_pypi(names)` — PyPI package name availability
- `check_npm(names)` — npm package name availability
- `check_crates(names)` — crates.io package name availability
- `check_docker_hub(names)` — Docker Hub namespace availability
- `check_homebrew(names)` — Homebrew formula name availability

All accept a list of names and return results for each.

### `brand_search_preferences`

Manage all preferences — service config, domain tiers, and creative style.
Call with no args to view current settings. Each parameter updates only its
section; omitted sections are unchanged.

```
brand_search_preferences()                    # view all
brand_search_preferences(services={"npm": false, "docker_hub": false})
brand_search_preferences(domain_tiers={"critical": [".com", ".dev"]})
brand_search_preferences(add_keywords=["fitness", "minimal"])
brand_search_preferences(add_liked_brands=["Stripe", "Notion"])
brand_search_preferences(add_guidelines=["short Spanish words", "must work as CLI command"])
brand_search_preferences(remove_keywords=["fitness"])
```

## Design: orchestrator vs. individual tools

The orchestrator (`check_name_availability`) runs all checks in parallel
internally and returns in one tool call — best for initial sweeps across many
candidates.

Individual tools (`check_domain`, `check_pypi`, etc.) return faster because
they only check one service — best for follow-up questions like "what about
the .ai domain?" or "is it on PyPI?"

The skill chooses the right tool for the moment:
- **Orchestrator** for batch comparison tables (fewer tool calls, one wait)
- **Individual tools** for targeted drill-downs (faster feedback per question)
- **Parallel individual tools** when checking one name across a few services
  and wanting results to trickle in

Examples:

```
User: "Give me 5 name ideas for my fitness tracker and check availability"
→ Skill brainstorms names, calls check_name_availability with all 5

User: "What about .ai for fitlog?"
→ Skill calls check_domain(names=["fitlog"], extensions=[".ai"])

User: "Is replog taken on PyPI or GitHub?"
→ Skill calls check_pypi and check_github_org in parallel

User: "I don't care about npm or Docker Hub"
→ Skill calls brand_search_preferences to save that
```

## Preferences

Preferences are stored at `~/.config/product-branding/preferences.json`
(respects `$XDG_CONFIG_HOME`). They persist across sessions and plugin
updates.

- **Services**: enable/disable domain, github_org, pypi, npm, crates,
  docker_hub, homebrew
- **Domain tiers**: categorize extensions as critical, nice_to_have,
  informational, or ignore. Ignored extensions are never checked.
- **Keywords**: terms meaningful to you for brainstorming (e.g. "fitness",
  "cloud", "personal tools")
- **Liked brands**: names you admire as style references (e.g. "Stripe",
  "Rye", "Bun")
- **Guidelines**: naming rules in your own words (e.g. "short Spanish words",
  "no weird misspellings", "must work as a CLI command")

## Prerequisites

- `gh` CLI (for GitHub org checks)
- `whois` (for domain checks)
- `brew` (for Homebrew checks, optional — degrades gracefully if missing)
