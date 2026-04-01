---
name: product-branding
description: >
  Name software products, check name availability, and help with product branding.
  Use when the user asks to name a product, brainstorm product names, check if a
  name is available, validate a name idea, help with branding, or compare name
  candidates. Triggers on: "what should I call", "name ideas", "product branding",
  "check availability", "is this name taken", "name my app/tool/project".
user-invocable: true
disable-model-invocation: false
---

# Product Branding & Name Discovery

Help the user find a strong, available name for a software product. This skill
covers brainstorming names AND checking availability across key namespaces.

## Tool strategy

This plugin provides MCP tools for availability checks. Choose the right tool
for the moment to optimize both UX (show results fast) and performance (minimize
round-trips):

- **`check_name_availability`** — the orchestrator. Use this for batch checks
  (e.g. 5+ candidates across all services). One tool call, all results. Best
  when the user is waiting for a comparison table. The user sees nothing until
  all checks finish, so use this when you want the full picture at once.

- **Individual tools** (`check_domain`, `check_github_org`, `check_pypi`,
  `check_npm`, `check_crates`, `check_docker_hub`, `check_homebrew`) — use
  these for targeted follow-ups. When the user says "what about .ai for that
  one?" or "check if X is on PyPI", call the specific tool. Results appear
  faster because you're not waiting for unrelated services. You can also call
  several in parallel for a single name to trickle results to the user.

- **`brand_search_preferences`** — manages search config and creative
  preferences: which services and domain tiers to check, plus keywords and
  naming guidelines. Call with no args to load current preferences. The
  orchestrator respects service/domain preferences automatically. You should
  load creative preferences at the start of a brainstorming session to inform
  your name generation — these are the user's saved taste and style cues.

- **Brand management tools** (`add_brand`, `update_brand`, `remove_brand`,
  `list_brands`) — manage the user's saved brand names separately from
  search preferences. Use `add_brand` to save a name with optional metadata
  (available namespaces, tags, notes). Use `update_brand` to modify metadata
  on individual brands after adding. Use `list_brands` to retrieve saved
  brands with optional filters (by tag, available namespace, or name search).
  Use `remove_brand` to delete brands the user no longer wants tracked.

**Rule of thumb:** Use the orchestrator for initial sweeps, individual tools
for drill-downs and iterations. When in doubt, prefer fewer tool calls — the
orchestrator runs its checks in parallel internally, so it's faster than
calling individual tools sequentially.

## Before brainstorming

Call `brand_search_preferences()` with no arguments to load the user's saved
preferences. This gives you:

- **Service config** — which availability checks to run
- **Domain tiers** — which extensions matter and how much
- **Keywords** — terms meaningful to the user (e.g. "fitness", "cloud")
- **Guidelines** — naming rules in the user's own words (e.g. "short Spanish
  words", "no weird misspellings", "must work as a CLI command")

Also call `list_brands()` to load saved brands from prior sessions. These
serve as style references and show what's already been researched. Check
availability data on saved brands — unchecked namespaces may need follow-up.

Use keywords and liked brands as creative fuel. Follow guidelines as
constraints. If this is the user's first time, preferences will be defaults —
offer to save their style preferences after the session.

When the user expresses style preferences during the conversation ("I like
short punchy names", "no weird misspellings"), save them via `brand_search_preferences`
so future sessions remember. Use the add/remove parameters to update individual
list items without replacing the whole set.

## Input gathering

Start by understanding what needs a name. Accept any combination of:

- **A description or pitch** of the product idea
- **A git repo or GitHub URL** — read the README and key files to understand
  the product
- **Multiple repos** for an ecosystem of related products
- **An existing name** the user wants to validate or find alternatives to

If given a repo path or URL, read `**/*.md` files (especially README.md,
CONTRIBUTING.md, docs/) and scan the codebase structure to understand the
product's purpose, audience, and technical domain.

Ask clarifying questions if needed:
- Target audience (developers, enterprises, end users)?
- Tone (playful, professional, technical, minimal)?
- Constraints (max length, must contain a keyword, must be a real word)?
- Is this part of a family of products that should share naming conventions?

## Name generation

Generate **at least 5 name candidates** per round. Aim for variety across these
styles:

| Style | Example patterns |
|-------|-----------------|
| **Descriptive** | What it does, literally (CloudSync, DataPipe) |
| **Metaphorical** | Evocative imagery (Lighthouse, Forge, Conduit) |
| **Portmanteau** | Blended words (Kubernetes, Grafana) |
| **Short/punchy** | 1-2 syllables, memorable (Deno, Bun, Rye) |
| **Abstract** | Coined words, no literal meaning (Vercel, Supabase) |
| **Domain-rooted** | References the technical domain (AgentKit, ToolChain) |

For AI/agent ecosystem products specifically, consider:
- References to agency, autonomy, orchestration, reasoning
- Names that work as both a CLI command and a brand
- Names that compose well with subcommands (`<name> deploy`, `<name> run`)
- Whether the name works as a Python/npm package import

## Availability checks

Use `check_name_availability` with all candidate names to get a single unified
result. The tool respects saved preferences for which services and domain tiers
to check.

For checks the MCP tools don't cover (web presence, VS Code Marketplace,
Twitter/X, Reddit, USPTO trademarks), use web search directly:

- **General web presence** — search for `"<name>" software` or
  `"<name>" developer tool`
- **VS Code Marketplace** — `site:marketplace.visualstudio.com "<name>"`
- **Twitter/X** — `site:x.com/<name>`
- **Reddit** — `site:reddit.com/r/<name>`
- **Trademark** — `"<name>" site:uspto.gov`

Only do web-search checks when the user asks for a deep-dive or the name is
a strong contender worth vetting thoroughly.

## Output format

Present results as a comparison table:

```
## Name Candidates

| # | Name | .com | .dev | GitHub Org | PyPI | Homebrew |
|---|------|------|------|------------|------|----------|
| 1 | ...  | ✅   | ❌   | ✅         | ✅   | ✅       |
| 2 | ...  | ❌   | ✅   | ✅         | ✅   | ❌       |

✅ = available  ❌ = taken  ⚠️ = unknown/error
```

Always use icons, never text like "avl" or "taken".

After the table, provide a **brief analysis** for each name:
- Pronunciation and memorability
- How it reads as a CLI command or import name
- Any potential confusion with existing products
- Domain alternatives if .com is taken (.dev, .io, .ai, .sh, .run, .tools)

Note which preferences were active (e.g., "Checked: domain (.com, .dev),
GitHub org, PyPI, Homebrew. Skipped: npm, crates, Docker Hub per your
preferences.").

## Iteration

After presenting results, ask if the user wants to:
1. **Explore variations** of a favorite (prefixes, suffixes, alternate TLDs)
2. **Generate more names** with adjusted criteria
3. **Deep-dive** a specific name (full trademark search, social handles, etc.)
4. **Check a name the user thought of** against all namespaces
5. **Adjust preferences** — change which services or domain tiers are checked
6. **Save style notes** — save keywords, liked brands, or naming guidelines
   for future sessions

For follow-up checks on a single name or service, use the individual tools
rather than the orchestrator — faster response, and the user sees results
immediately.

## Tips

- `whois` output varies by registrar. The domain check tool handles this, but
  results can occasionally be ambiguous — flag those to the user.
- Some names will be taken everywhere — that's fine, include them if the name
  is strong. Note what's available and what's not.
- For package registries, also suggest common variations (hyphenated, with
  `-py` or `-js` suffix, prefixed with `py-` or `node-`).
- If a name is taken on GitHub but available as `<name>-dev`, `<name>-hq`,
  `<name>-io`, or `get<name>`, mention that as an alternative.
