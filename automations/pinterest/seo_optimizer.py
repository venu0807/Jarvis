"""
SEO Optimizer - Minimal stub for fallback SEO generation.
The main generator.py has fallback logic when LLM is not available.
"""

def get_llm_seo_optimized(name: str, category: str, price: str = None):
    """
    Returns (seo_title, seo_description) or (None, None) if LLM not available.
    Falls back to deterministic templates in generator.py.
    """
    # LLM not configured - return None to trigger fallback in generator.py
    return None, None


def optimize_csv_column():
    """Placeholder for CSV SEO optimization."""
    print("  ℹ️  SEO optimizer not configured - using generator fallbacks")


def seo_variants():
    """Placeholder for SEO variants."""
    return []