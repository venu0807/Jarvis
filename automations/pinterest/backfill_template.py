"""
backfill_template.py — One-time migration script.

Adds a `Pin_Template` column to data.csv. For existing rows, picks a 
sensible default based on the product's category + price + tags:

  product_overlay (default)
  big_number      (cheap items, under $25)
  comparison      (tech/gadget items, "vs" angle)
  review_quote    (trending / viral items)
  content         (already content pins)

Idempotent — safe to run multiple times.
"""

import os
import sys
import pandas as pd
from database import get_products_df, save_products_df

CSV_FILE = "data.csv"


def pick_default_template(row) -> str:
    """Best-effort guess at the right template for an existing row."""
    pin_type = str(row.get("Pin Type", "")).lower().strip()
    if pin_type == "content":
        return "content"

    price = str(row.get("Price", "")).strip()
    tags = str(row.get("Tags", "")).lower()
    category = str(row.get("Category", "")).lower()

    # Cheap items → big_number template (under-$X angles)
    try:
        # Extract numeric
        digits = "".join(c for c in price if c.isdigit())
        if digits and int(digits) <= 25:
            return "big_number"
    except (ValueError, AttributeError):
        pass

    # Tech / gadgets / comparison hooks → comparison
    if "tech" in category or " vs " in tags or "comparison" in tags:
        return "comparison"

    # Trending / viral content → review_quote (trust-building)
    if any(kw in tags for kw in ["trending", "viral", "popular"]):
        return "review_quote"

    return "product_overlay"


def main():
    if not True:
        print(f"  ❌ {CSV_FILE} not found.")
        sys.exit(1)

    df = get_products_df().fillna("")

    # Add Pin_Template column if missing
    if "Pin_Template" not in df.columns:
        df.insert(len(df.columns), "Pin_Template", "")
        print("  ✅ Added 'Pin_Template' column")

    # Backfill empties
    empty_count = (df["Pin_Template"].astype(str).str.strip() == "").sum()
    print(f"  📊 Rows with empty Pin_Template: {empty_count}")

    if empty_count == 0:
        print("  ✅ All rows already have a Pin_Template value")
        return

    new_values = []
    for _, row in df.iterrows():
        existing = str(row.get("Pin_Template", "")).strip()
        if existing:
            new_values.append(existing)
            continue
        new_values.append(pick_default_template(row))

    df["Pin_Template"] = new_values
    save_products_df(df)

    # Show distribution
    from collections import Counter
    counts = Counter(new_values)
    print(f"\n  ✅ Backfilled {empty_count} rows. New distribution:")
    for tpl, count in counts.most_common():
        print(f"     • {tpl:18} {count}")

    print(f"\n  💡 Tip: edit Pin_Template per row in {CSV_FILE} to force a layout.")


if __name__ == "__main__":
    main()
