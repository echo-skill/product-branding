"""Product branding MCP server — name availability checks across namespaces."""

import asyncio
import json
import os
import subprocess
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("product-branding")

# --- Config ---

_xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
CONFIG_PATH = Path(_xdg_config) / "product-branding" / "preferences.json"

DEFAULT_CONFIG = {
    "services": {
        "domain": True,
        "github_org": True,
        "pypi": True,
        "npm": False,
        "crates": False,
        "docker_hub": False,
        "homebrew": True,
    },
    "domain_tiers": {
        "critical": [".com", ".dev"],
        "nice_to_have": [".io"],
        "informational": [".ai"],
        "ignore": [],
    },
    "creative": {
        "keywords": [],
        "liked_brands": [],
        "guidelines": [],
    },
}

CREATIVE_LIST_FIELDS = {"keywords", "liked_brands", "guidelines"}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        saved = json.loads(CONFIG_PATH.read_text())
        # Merge with defaults so new keys are picked up
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        for section in ("services", "domain_tiers", "creative"):
            if section in saved:
                config[section].update(saved[section])
        return config
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


# --- Individual check tools ---


@mcp.tool()
async def check_domain(
    names: list[str],
    extensions: list[str] | None = None,
) -> dict:
    """Check domain availability via whois for one or more names.

    Args:
        names: Product names to check.
        extensions: Domain extensions to check (e.g. [".com", ".dev"]).
                    If omitted, uses all non-ignored extensions from preferences.
    """
    config = load_config()
    if extensions is None:
        tiers = config["domain_tiers"]
        extensions = []
        for tier in ("critical", "nice_to_have", "informational"):
            extensions.extend(tiers.get(tier, []))

    results = {}
    for name in names:
        results[name] = {}
        for ext in extensions:
            domain = f"{name}{ext}"
            results[name][ext] = await _whois_check(domain)

    return results


async def _whois_check(domain: str) -> dict:
    """Run whois and determine availability."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "whois", domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        output = stdout.decode("utf-8", errors="replace")
        available_signals = [
            "no match",
            "not found",
            "domain not found",
            "no data found",
            "available",
            "no entries found",
            "status: free",
        ]
        output_lower = output.lower()
        available = any(s in output_lower for s in available_signals)
        return {"available": available, "domain": domain}
    except asyncio.TimeoutError:
        return {"available": None, "domain": domain, "error": "timeout"}
    except Exception as e:
        return {"available": None, "domain": domain, "error": str(e)}


@mcp.tool()
async def check_github_org(names: list[str]) -> dict:
    """Check GitHub organization/user name availability for one or more names.

    Args:
        names: Names to check as GitHub org/user names.
    """
    results = {}
    for name in names:
        results[name] = await _gh_user_check(name)
    return results


async def _gh_user_check(name: str) -> dict:
    """Check if a GitHub user/org exists."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh", "api", f"/users/{name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")
            if "404" in err or "Not Found" in err:
                return {"available": True}
            return {"available": None, "error": err.strip()}
        # Exists — parse for useful info
        try:
            data = json.loads(stdout.decode("utf-8"))
            return {
                "available": False,
                "type": data.get("type", "Unknown"),
                "name": data.get("name"),
                "public_repos": data.get("public_repos", 0),
            }
        except json.JSONDecodeError:
            return {"available": False}
    except asyncio.TimeoutError:
        return {"available": None, "error": "timeout"}
    except Exception as e:
        return {"available": None, "error": str(e)}


@mcp.tool()
async def check_pypi(names: list[str]) -> dict:
    """Check PyPI package name availability for one or more names.

    Args:
        names: Package names to check on PyPI.
    """
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name in names:
            results[name] = await _pypi_check(client, name)
    return results


async def _pypi_check(client: httpx.AsyncClient, name: str) -> dict:
    """Check if a PyPI package exists."""
    try:
        resp = await client.get(f"https://pypi.org/pypi/{name}/json")
        if resp.status_code == 404:
            return {"available": True}
        if resp.status_code == 200:
            data = resp.json()
            info = data.get("info", {})
            return {
                "available": False,
                "summary": info.get("summary", ""),
                "version": info.get("version", ""),
            }
        return {"available": None, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"available": None, "error": str(e)}


@mcp.tool()
async def check_npm(names: list[str]) -> dict:
    """Check npm package name availability for one or more names.

    Args:
        names: Package names to check on npm.
    """
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name in names:
            results[name] = await _npm_check(client, name)
    return results


async def _npm_check(client: httpx.AsyncClient, name: str) -> dict:
    """Check if an npm package exists."""
    try:
        resp = await client.get(f"https://registry.npmjs.org/{name}")
        if resp.status_code == 404:
            return {"available": True}
        if resp.status_code == 200:
            data = resp.json()
            return {
                "available": False,
                "description": data.get("description", ""),
                "latest": data.get("dist-tags", {}).get("latest", ""),
            }
        return {"available": None, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"available": None, "error": str(e)}


@mcp.tool()
async def check_crates(names: list[str]) -> dict:
    """Check crates.io package name availability for one or more names.

    Args:
        names: Crate names to check.
    """
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name in names:
            results[name] = await _crates_check(client, name)
    return results


async def _crates_check(client: httpx.AsyncClient, name: str) -> dict:
    """Check if a crate exists."""
    try:
        resp = await client.get(
            f"https://crates.io/api/v1/crates/{name}",
            headers={"User-Agent": "product-branding-checker"},
        )
        if resp.status_code == 404:
            return {"available": True}
        if resp.status_code == 200:
            data = resp.json()
            crate = data.get("crate", {})
            return {
                "available": False,
                "description": crate.get("description", ""),
                "downloads": crate.get("downloads", 0),
            }
        return {"available": None, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"available": None, "error": str(e)}


@mcp.tool()
async def check_docker_hub(names: list[str]) -> dict:
    """Check Docker Hub namespace availability for one or more names.

    Args:
        names: Names to check as Docker Hub namespaces.
    """
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for name in names:
            results[name] = await _docker_check(client, name)
    return results


async def _docker_check(client: httpx.AsyncClient, name: str) -> dict:
    """Check if a Docker Hub namespace exists."""
    try:
        resp = await client.get(
            f"https://hub.docker.com/v2/orgs/{name}/",
        )
        if resp.status_code == 404:
            return {"available": True}
        if resp.status_code == 200:
            return {"available": False}
        return {"available": None, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"available": None, "error": str(e)}


@mcp.tool()
async def check_homebrew(names: list[str]) -> dict:
    """Check Homebrew formula/cask name availability for one or more names.

    Args:
        names: Formula names to check in Homebrew.
    """
    results = {}
    for name in names:
        results[name] = await _brew_check(name)
    return results


async def _brew_check(name: str) -> dict:
    """Check if a Homebrew formula exists."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "brew", "info", name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")
            if "No available formula" in err or "No formulae or casks" in err:
                return {"available": True}
            return {"available": None, "error": err.strip()[:200]}
        return {"available": False}
    except asyncio.TimeoutError:
        return {"available": None, "error": "timeout"}
    except FileNotFoundError:
        return {"available": None, "error": "brew not installed"}
    except Exception as e:
        return {"available": None, "error": str(e)}


# --- Orchestrator ---


@mcp.tool()
async def check_name_availability(
    names: list[str],
    services: list[str] | None = None,
) -> dict:
    """Check name availability across multiple services at once.

    Runs all enabled checks in parallel and returns a unified result.
    Shows which preferences are active in the response.

    Args:
        names: One or more product names to check.
        services: Override which services to check. If omitted, uses saved
                  preferences. Valid values: domain, github_org, pypi, npm,
                  crates, docker_hub, homebrew.
    """
    config = load_config()
    active_services = config["services"]

    if services is not None:
        # Override: only check specified services
        active_services = {s: (s in services) for s in active_services}

    enabled = [s for s, on in active_services.items() if on]

    tasks = {}
    if "domain" in enabled:
        tasks["domain"] = check_domain(names)
    if "github_org" in enabled:
        tasks["github_org"] = check_github_org(names)
    if "pypi" in enabled:
        tasks["pypi"] = check_pypi(names)
    if "npm" in enabled:
        tasks["npm"] = check_npm(names)
    if "crates" in enabled:
        tasks["crates"] = check_crates(names)
    if "docker_hub" in enabled:
        tasks["docker_hub"] = check_docker_hub(names)
    if "homebrew" in enabled:
        tasks["homebrew"] = check_homebrew(names)

    # Run all checks in parallel
    keys = list(tasks.keys())
    raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    service_results = {}
    for key, result in zip(keys, raw_results):
        if isinstance(result, Exception):
            service_results[key] = {"error": str(result)}
        else:
            service_results[key] = result

    return {
        "names": names,
        "active_services": enabled,
        "domain_tiers": config["domain_tiers"] if "domain" in enabled else None,
        "results": service_results,
    }


# --- Preferences ---


def _brand_name(item) -> str:
    """Extract the name string from a liked_brands entry (str or dict)."""
    if isinstance(item, dict):
        return item.get("name", "")
    return item


def _normalize_brand(item) -> dict:
    """Ensure a liked_brands entry is in dict form.

    Migrates old formats:
      - Plain string "echoark" → {"name": "echoark"}
      - Old available list ["github", ".com"] →
        [{"type": "github", "status": "available"}, ...]
    """
    if isinstance(item, str):
        return {"name": item}
    # Migrate old-style available (list of strings) to new format
    if "available" in item and item["available"] and isinstance(item["available"][0], str):
        item["availability"] = [
            {"type": ns, "status": "available"} for ns in item["available"]
        ]
        del item["available"]
    return item


@mcp.tool()
async def brand_search_preferences(
    services: dict[str, bool] | None = None,
    domain_tiers: dict[str, list[str]] | None = None,
    add_keywords: list[str] | None = None,
    remove_keywords: list[str] | None = None,
    add_guidelines: list[str] | None = None,
    remove_guidelines: list[str] | None = None,
) -> dict:
    """Get or update preferences for brand name availability searches.

    Call with no arguments to load all current preferences. Load preferences
    at the start of any branding session to inform name generation and
    availability checks.

    Each parameter updates only its own section — omitted sections unchanged.

    This tool manages search configuration and creative preferences (keywords,
    guidelines). For managing saved brand names, use the dedicated brand tools:
      - add_brand: Save a new brand with optional metadata
      - update_brand: Modify metadata on an existing brand
      - remove_brand: Delete a brand from the saved list

    Args:
        services: Enable/disable services for availability sweeps.
                  Keys: domain, github_org, pypi, npm, crates, docker_hub,
                  homebrew. Values: true/false.
        domain_tiers: Categorize domain extensions by importance.
                      Keys: critical, nice_to_have, informational, ignore.
                      Values: lists of extensions (e.g. [".com", ".dev"]).
        add_keywords: Brainstorming inspiration words. Appended, deduplicated.
        remove_keywords: Keywords to remove.
        add_guidelines: Naming rules that persist across sessions and guide
                        name generation (e.g. "check both hyphenated and
                        unhyphenated versions").
        remove_guidelines: Guidelines to remove.
    """
    config = load_config()

    has_updates = any(v is not None for v in (
        services, domain_tiers,
        add_keywords, remove_keywords,
        add_guidelines, remove_guidelines,
    ))

    if not has_updates:
        return {"preferences": config, "source": str(CONFIG_PATH)}

    if services is not None:
        config["services"].update(services)
    if domain_tiers is not None:
        config["domain_tiers"].update(domain_tiers)

    creative = config["creative"]

    list_ops = [
        ("keywords", add_keywords, remove_keywords),
        ("guidelines", add_guidelines, remove_guidelines),
    ]
    for field, to_add, to_remove in list_ops:
        items = creative.get(field, [])
        if to_add:
            items.extend(to_add)
            seen = set()
            deduped = []
            for item in items:
                if item not in seen:
                    seen.add(item)
                    deduped.append(item)
            items = deduped
        if to_remove:
            remove_set = set(to_remove)
            items = [i for i in items if i not in remove_set]
        creative[field] = items

    save_config(config)
    return {"preferences": config, "updated": True, "source": str(CONFIG_PATH)}


@mcp.tool()
async def add_brand(
    name: str,
    availability: list[dict] | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    """Save a brand name to the liked brands list with optional metadata.

    If a brand with the same name already exists, its metadata is merged
    (new fields overwrite, existing fields not mentioned are preserved).

    Args:
        name: The brand name to save (e.g. "echoark").
        availability: Checked namespaces with explicit status. Each entry:
                      {"type": "<namespace>", "status": "<status>"}.
                      type: "github", ".com", ".dev", ".io", ".ai", "pypi",
                            "npm", "homebrew", etc.
                      status: "available", "unavailable", or "unknown".
                      Only include namespaces that have been checked. Absence
                      of a namespace means it hasn't been checked at all.
                      Example: [{"type": "github", "status": "available"},
                                {"type": ".com", "status": "unavailable"}]
        tags: Free-form labels for filtering and recall. Use for sentiment
              ("liked", "favorite", "killed"), purpose ("dev-tools",
              "ai-ecosystem"), or status ("finalist"). No fixed vocabulary.
        notes: Free-text context about this brand.
    """
    config = load_config()
    creative = config["creative"]
    brands = [_normalize_brand(b) for b in creative.get("liked_brands", [])]

    new_brand = {"name": name}
    if availability is not None:
        new_brand["availability"] = availability
    if tags is not None:
        new_brand["tags"] = tags
    if notes is not None:
        new_brand["notes"] = notes

    existing = next((b for b in brands if _brand_name(b) == name), None)
    if existing:
        existing.update(new_brand)
        brand = existing
    else:
        brands.append(new_brand)
        brand = new_brand

    creative["liked_brands"] = brands
    save_config(config)
    return {"brand": brand, "merged": existing is not None}


@mcp.tool()
async def remove_brand(
    names: list[str],
) -> dict:
    """Remove one or more brands from the liked brands list.

    Args:
        names: Brand names to remove (matched exactly by name string).
    """
    config = load_config()
    creative = config["creative"]
    brands = [_normalize_brand(b) for b in creative.get("liked_brands", [])]

    remove_set = set(names)
    before_count = len(brands)
    brands = [b for b in brands if _brand_name(b) not in remove_set]
    removed_count = before_count - len(brands)

    creative["liked_brands"] = brands
    save_config(config)
    return {"removed": removed_count, "remaining": len(brands)}


def _availability_status(brand: dict, namespace: str) -> str | None:
    """Get availability status for a namespace, or None if not checked."""
    for entry in brand.get("availability", []):
        if entry.get("type") == namespace:
            return entry.get("status")
    return None


@mcp.tool()
async def list_brands(
    tag: str | None = None,
    available_on: str | None = None,
    unavailable_on: str | None = None,
    unchecked_on: str | None = None,
    search: str | None = None,
) -> dict:
    """List saved brands with optional filters.

    Call with no arguments to list all saved brands. Filters can be combined
    (AND logic — all conditions must match).

    Args:
        tag: Filter to brands that have this tag (e.g. "finalist",
             "dev-tools", "killed").
        available_on: Filter to brands where this namespace has status
                      "available" (e.g. "github", ".com").
        unavailable_on: Filter to brands where this namespace has status
                        "unavailable".
        unchecked_on: Filter to brands where this namespace has NOT been
                      checked at all (not present in availability list).
                      Useful for finding brands that need follow-up checks.
        search: Substring match against brand name (case-insensitive).
    """
    config = load_config()
    brands = [_normalize_brand(b) for b in
              config.get("creative", {}).get("liked_brands", [])]

    if tag:
        brands = [b for b in brands if tag in b.get("tags", [])]
    if available_on:
        brands = [b for b in brands
                  if _availability_status(b, available_on) == "available"]
    if unavailable_on:
        brands = [b for b in brands
                  if _availability_status(b, unavailable_on) == "unavailable"]
    if unchecked_on:
        brands = [b for b in brands
                  if _availability_status(b, unchecked_on) is None]
    if search:
        search_lower = search.lower()
        brands = [b for b in brands if search_lower in _brand_name(b).lower()]

    return {"brands": brands, "count": len(brands)}


@mcp.tool()
async def update_brand(
    name: str,
    tags: list[str] | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
    notes: str | None = None,
    add_comments: list[str] | None = None,
    clear_fields: list[str] | None = None,
) -> dict:
    """Update tags, notes, or comments on a saved brand.

    For availability changes, use update_brand_availability instead.

    Args:
        name: Brand name to update (must match an existing liked brand).
        tags: Replace the full tags list. Free-form labels for filtering:
              sentiment ("liked", "favorite", "killed"), purpose
              ("dev-tools", "ai-ecosystem"), or status ("finalist").
        add_tags: Append tags without replacing existing ones.
        remove_tags: Remove specific tags.
        notes: Set free-text notes (replaces previous value).
        add_comments: Append one or more comments. Each is stored with a
                      timestamp automatically.
        clear_fields: Field names to remove entirely from this brand
                      (e.g. ["tags", "notes"]). Cannot clear "name".
    """
    config = load_config()
    creative = config["creative"]
    brands = [_normalize_brand(b) for b in creative.get("liked_brands", [])]

    brand = next((b for b in brands if _brand_name(b) == name), None)
    if brand is None:
        return {"error": f"Brand '{name}' not found in liked_brands. Add it first."}

    if clear_fields:
        for field in clear_fields:
            if field != "name":
                brand.pop(field, None)

    if tags is not None:
        brand["tags"] = tags
    if add_tags:
        existing_tags = brand.get("tags", [])
        existing_tags.extend(add_tags)
        brand["tags"] = list(dict.fromkeys(existing_tags))
    if remove_tags:
        brand["tags"] = [t for t in brand.get("tags", []) if t not in set(remove_tags)]
    if notes is not None:
        brand["notes"] = notes
    if add_comments:
        from datetime import datetime, timezone
        comments = brand.get("comments", [])
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for comment in add_comments:
            comments.append(f"[{ts}] {comment}")
        brand["comments"] = comments

    creative["liked_brands"] = brands
    save_config(config)
    return {"brand": brand, "updated": True}


@mcp.tool()
async def update_brand_availability(
    name: str,
    entries: list[dict],
    reset: bool = False,
) -> dict:
    """Set or merge availability data on a saved brand.

    Each entry records whether a namespace is available, unavailable, or
    unknown. Namespaces not mentioned are left unchanged (unless reset=True).

    Availability uses three-state semantics:
      - "available": confirmed open, can be registered now.
      - "unavailable": confirmed taken.
      - "unknown": checked but result was ambiguous (e.g. whois timeout).
      - Not in list at all: never checked — distinct from all three above.

    Args:
        name: Brand name to update (must match an existing liked brand).
        entries: Namespace availability entries. Each is a dict with:
                 "type" (e.g. "github", ".com", ".ai", "pypi") and
                 "status" ("available", "unavailable", or "unknown").
                 Entries for types already present are overwritten;
                 new types are appended.
        reset: If true, replace all existing availability with entries.
               If false (default), merge entries into existing data.
    """
    config = load_config()
    creative = config["creative"]
    brands = [_normalize_brand(b) for b in creative.get("liked_brands", [])]

    brand = next((b for b in brands if _brand_name(b) == name), None)
    if brand is None:
        return {"error": f"Brand '{name}' not found in liked_brands. Add it first."}

    if reset:
        brand["availability"] = entries
    else:
        existing = brand.get("availability", [])
        for entry in entries:
            ns_type = entry["type"]
            found = next((e for e in existing if e["type"] == ns_type), None)
            if found:
                found["status"] = entry["status"]
            else:
                existing.append(entry)
        brand["availability"] = existing

    creative["liked_brands"] = brands
    save_config(config)
    return {"brand": brand, "updated": True}


if __name__ == "__main__":
    mcp.run(transport="stdio")
