"""Small tool-using catalog quality agent.

This MVP intentionally uses deterministic tools instead of an LLM so checks are
reproducible, fast, and safe to demo offline. It reports recommendations only;
no product values are silently changed.
"""
from collections import Counter


def tool_check_required_fields(products):
    findings = []
    for p in products:
        for field, label in (("name", "Product name"), ("sku", "SKU"), ("category", "Category"), ("description", "Description")):
            if not str(p.get(field, "")).strip():
                findings.append({"product_id": p["id"], "sku": p.get("sku") or "—", "product": p.get("name") or "Unnamed product",
                                 "field": field, "severity": "warning", "issue": f"{label} is missing.",
                                 "recommendation": f"Add a meaningful {label.lower()} before publishing."})
    return findings


def tool_check_numeric_values(products):
    findings = []
    for p in products:
        if float(p.get("price", 0)) <= 0:
            findings.append({"product_id": p["id"], "sku": p.get("sku") or "—", "product": p.get("name") or "Unnamed product",
                             "field": "price", "severity": "critical", "issue": "Price must be greater than zero for a sellable item.",
                             "recommendation": "Confirm the intended selling price and enter a positive amount."})
        if int(p.get("stock", 0)) < 0:
            findings.append({"product_id": p["id"], "sku": p.get("sku") or "—", "product": p.get("name") or "Unnamed product",
                             "field": "stock", "severity": "critical", "issue": "Stock cannot be negative.",
                             "recommendation": "Reconcile inventory and enter zero or a positive whole number."})
    return findings


def tool_check_duplicate_skus(products):
    counts = Counter(str(p.get("sku", "")).strip().casefold() for p in products if str(p.get("sku", "")).strip())
    duplicate_skus = {sku for sku, count in counts.items() if count > 1}
    findings = []
    for p in products:
        sku = str(p.get("sku", "")).strip().casefold()
        if sku in duplicate_skus:
            findings.append({"product_id": p["id"], "sku": p.get("sku") or "—", "product": p.get("name") or "Unnamed product",
                             "field": "sku", "severity": "critical", "issue": "SKU is duplicated in the catalog.",
                             "recommendation": "Assign a unique SKU; SKU is the product matching key for reliable synchronization."})
    return findings


TOOLS = {
    "required_fields": tool_check_required_fields,
    "numeric_values": tool_check_numeric_values,
    "duplicate_skus": tool_check_duplicate_skus,
}


def audit_catalog(products):
    """Plan -> call validation tools -> rank findings -> summarize."""
    plan = ["Check required product attributes", "Validate price and stock", "Detect duplicate SKUs"]
    findings = []
    for tool in TOOLS.values():
        findings.extend(tool(products))
    rank = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: (rank.get(item["severity"], 9), item["product"].casefold()))
    return {
        "agent_name": "Catalog Quality Agent",
        "mode": "Deterministic tool-assisted audit",
        "plan": plan,
        "tools_used": list(TOOLS.keys()),
        "products_scanned": len(products),
        "issues_found": len(findings),
        "critical_count": sum(f["severity"] == "critical" for f in findings),
        "warning_count": sum(f["severity"] == "warning" for f in findings),
        "findings": findings,
        "summary": "Catalog checks completed. Recommendations require human review; no product data was changed.",
    }
