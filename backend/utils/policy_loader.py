"""Load and retrieve policy docs by scenario using deterministic section lookup."""

import os
from functools import lru_cache

POLICY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "policies")


def _parse_sections(filepath: str) -> dict[str, str]:
    """Parse a markdown file into {heading: content} sections."""
    sections = {}
    current_heading = None
    current_lines = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#"):
                if current_heading is not None:
                    sections[current_heading.lower()] = "\n".join(current_lines).strip()
                heading_text = stripped.lstrip("#").strip()
                current_heading = heading_text
                current_lines = []
            else:
                current_lines.append(line.rstrip())

    if current_heading is not None:
        sections[current_heading.lower()] = "\n".join(current_lines).strip()

    return sections


@lru_cache(maxsize=4)
def _load_policy(filename: str) -> dict[str, str]:
    return _parse_sections(os.path.join(POLICY_DIR, filename))


def _get_section(filename: str, heading_substring: str) -> str:
    """Find the first section whose heading contains the substring (case-insensitive)."""
    sections = _load_policy(filename)
    key = heading_substring.lower()
    for heading, content in sections.items():
        if key in heading:
            return f"### {heading}\n{content}"
    return ""


def get_relevant_policy(product_type: str, refund_reason: str, scenario_flags: list[str] | None = None) -> str:
    """
    Load the relevant policy snippet based on deterministic tags.
    The engine already knows the product type, refund reason, and scenario.
    We just fetch the matching section from the markdown files.
    """
    snippets = []

    if product_type in ("cancelable", "partially_refundable"):
        if product_type == "cancelable":
            snippets.append(_get_section("cancellation_policy.md", "cancelable products"))
        else:
            snippets.append(_get_section("cancellation_policy.md", "partially refundable"))
    elif product_type == "non_cancelable":
        snippets.append(_get_section("cancellation_policy.md", "non‑cancelable"))
        if not snippets[-1]:
            snippets[-1] = _get_section("cancellation_policy.md", "non-cancelable")

    if refund_reason == "no_show":
        snippets.append(_get_section("cancellation_policy.md", "no‑show policy"))
        if not snippets[-1]:
            snippets.append(_get_section("cancellation_policy.md", "no-show"))

    if refund_reason == "partial_service":
        snippets.append(_get_section("agent_response_guidelines.md", "offering a partial refund"))

    if refund_reason == "technical_issue":
        snippets.append(_get_section("agent_response_guidelines.md", "when confirmation was never sent"))

    flags = scenario_flags or []
    if "customer_aggressive" in flags or "chargeback_threat" in flags:
        snippets.append(_get_section("agent_response_guidelines.md", "handling aggression"))
        snippets.append(_get_section("agent_response_guidelines.md", "handling escalating situations"))

    if product_type == "cancelable":
        snippets.append(_get_section("agent_response_guidelines.md", "approving a refund"))

    return "\n\n".join(s for s in snippets if s)


def get_escalation_policy() -> str:
    """Return policy sections needed for contextual guidance LLM calls."""
    sections = [
        _get_section("escalation_criteria.md", "l1 resolution authority"),
        _get_section("escalation_criteria.md", "mandatory escalation triggers"),
        _get_section("agent_response_guidelines.md", "handling escalating situations"),
    ]
    return "\n\n".join(s for s in sections if s)


def get_supplier_context(supplier_type: str) -> str:
    """Return the supplier type reference section."""
    type_map = {
        "direct_contract": "direct contract",
        "aggregator": "aggregator partner",
        "last_minute_marketplace": "last‑minute marketplace",
    }
    key = type_map.get(supplier_type, supplier_type)
    result = _get_section("supplier_types_reference.md", key)
    if not result:
        result = _get_section("supplier_types_reference.md", supplier_type.replace("_", " "))
    return result
