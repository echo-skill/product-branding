# Tools Reference

Complete MCP tool interface documentation for the product-branding plugin.

## Availability checks

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

## Preferences

### `brand_search_preferences`

Manage search config and creative preferences — services, domain tiers,
keywords, and naming guidelines. Call with no args to view current settings.
Each parameter updates only its section; omitted sections are unchanged.

```
brand_search_preferences()                    # view all
brand_search_preferences(services={"npm": false, "docker_hub": false})
brand_search_preferences(domain_tiers={"critical": [".com", ".dev"]})
brand_search_preferences(add_keywords=["fitness", "minimal"])
brand_search_preferences(add_guidelines=["must work as CLI command"])
brand_search_preferences(remove_keywords=["fitness"])
```

## Brand management

### `add_brand`

Save a brand with optional availability data, tags, and notes. If a brand
with the same name already exists, new fields are merged into the existing
entry.

```
add_brand(name="echoark")
add_brand(
    name="echoark",
    availability=[
        {"type": "github", "status": "available"},
        {"type": ".com", "status": "unavailable"},
        {"type": ".io", "status": "available"}
    ],
    tags=["dev-tools", "finalist"],
    notes="Ark = vessel/preservation. No .com but echoark.io works."
)
```

### `update_brand`

Modify tags, notes, or comments on an existing brand. For availability
changes, use `update_brand_availability` instead.

```
update_brand(name="echoark", add_tags=["favorite"])
update_brand(name="echoark", tags=["finalist"])          # replace all tags
update_brand(name="echoark", remove_tags=["draft"])
update_brand(name="echoark", notes="Updated: confirmed .io available")
update_brand(name="echoark", add_comments=["Loves the ark metaphor"])
update_brand(name="echoark", clear_fields=["tags", "notes"])  # remove fields
```

### `update_brand_availability`

Set or merge availability data on a brand. Merge by default; pass
`reset=True` to replace all existing entries.

```
update_brand_availability(
    name="echoark",
    entries=[{"type": ".ai", "status": "available"}]
)
update_brand_availability(
    name="echoark",
    entries=[
        {"type": "github", "status": "available"},
        {"type": ".com", "status": "unavailable"}
    ],
    reset=True
)
```

Availability uses three-state semantics per namespace:
- `"available"` — confirmed open, can be registered now
- `"unavailable"` — confirmed taken
- `"unknown"` — checked but result was ambiguous (e.g. whois timeout)
- Not in list at all — never checked (distinct from all three above)

### `list_brands`

Query saved brands with optional filters. Filters combine with AND logic.

```
list_brands()                              # all brands
list_brands(tag="finalist")                # by tag
list_brands(available_on="github")         # available on a namespace
list_brands(unavailable_on=".com")         # taken on a namespace
list_brands(unchecked_on="pypi")           # needs follow-up check
list_brands(search="echo")                 # name substring match
```

### `remove_brand`

Delete one or more brands by name.

```
remove_brand(names=["oldname", "badidea"])
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
