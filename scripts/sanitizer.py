import re

class SanitizerMiddleware:
    """
    Middleware to mask Personally Identifiable Information (PII) before sending 
    data to Cloud LLMs (e.g., OpenRouter, Nvidia).
    
    Currently implements fast Regex-based masking. 
    Can be extended to use a local LLM (like ollama/phi3) for semantic masking.
    """
    def __init__(self, strict=True):
        self.strict = strict
        # Standard Regex Patterns for PII
        self.patterns = {
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "PHONE": r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
            "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
            # Add custom generic strings to block (e.g. your real name, address)
            "NAME": r"\b(Venu|Venu\s[A-Za-z]+)\b", 
        }

    def mask_text(self, text: str) -> str:
        """Applies all regex patterns to mask sensitive data in a string."""
        if not text:
            return text
            
        masked_text = text
        for label, pattern in self.patterns.items():
            masked_text = re.sub(pattern, f"<{label}>", masked_text, flags=re.IGNORECASE)
            
        return masked_text

    def mask_payload(self, payload: dict) -> dict:
        """Recursively masks strings within a JSON/dict payload."""
        if isinstance(payload, str):
            return self.mask_text(payload)
        elif isinstance(payload, dict):
            return {k: self.mask_payload(v) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [self.mask_payload(item) for item in payload]
        else:
            return payload

    def unmask_text(self, text: str, mapping: dict) -> str:
        """
        Future implementation: Restore the masked data from the cloud's response
        using a mapping table if the agent needs the exact values back.
        """
        # For now, Openclaw usually doesn't need to unmask if it's just generating code/logic.
        pass

if __name__ == "__main__":
    # Quick Test
    sanitizer = SanitizerMiddleware()
    test_str = "Contact Venu at venu@example.com or call +1-555-019-8372."
    print("Original:", test_str)
    print("Masked:  ", sanitizer.mask_text(test_str))
