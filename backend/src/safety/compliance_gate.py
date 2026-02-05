"""
Compliance and safety filtering for BeatCanvas backend.
Placeholder implementation with simple keyword-based filtering.
"""
import os
import re
from typing import Tuple, Optional, List


class ComplianceGate:
    """
    Simple content compliance checker.

    This is a placeholder implementation. In production, you would integrate:
    - LlamaGuard or similar safety model
    - Custom trained classifiers
    - Third-party moderation APIs
    """

    # Default banned keywords (can be configured via environment or config file)
    DEFAULT_BANNED_KEYWORDS = [
        # Add your safety keywords here
        "violence", "gore", "nsfw",
        # Placeholder list - customize based on your requirements
    ]

    def __init__(
        self,
        enable_safety: bool = None,
        banned_keywords: Optional[List[str]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize the compliance gate.

        Args:
            enable_safety: Enable safety checks (default: from ENABLE_SAFETY env var)
            banned_keywords: Custom list of banned keywords
            strict_mode: If True, apply stricter filtering
        """
        # Check environment variable
        if enable_safety is None:
            enable_safety = os.getenv("ENABLE_SAFETY", "true").lower() == "true"

        self.enabled = enable_safety
        self.strict_mode = strict_mode

        # Set banned keywords
        if banned_keywords is not None:
            self.banned_keywords = [kw.lower() for kw in banned_keywords]
        else:
            self.banned_keywords = [kw.lower() for kw in self.DEFAULT_BANNED_KEYWORDS]

        print(f"ComplianceGate initialized (enabled={self.enabled}, strict={strict_mode})")

    def check_prompt(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a prompt passes safety filters.

        Args:
            prompt: The prompt to check

        Returns:
            Tuple[bool, Optional[str]]: (is_safe, reason_if_blocked)
        """
        if not self.enabled:
            # Safety disabled - pass through
            return True, None

        prompt_lower = prompt.lower()

        # Check for banned keywords
        for keyword in self.banned_keywords:
            if keyword in prompt_lower:
                reason = f"Prompt contains banned keyword: '{keyword}'"
                return False, reason

        # In strict mode, apply additional checks
        if self.strict_mode:
            # Example: Check for excessive caps (often indicates aggressive content)
            caps_ratio = sum(1 for c in prompt if c.isupper()) / max(len(prompt), 1)
            if caps_ratio > 0.5 and len(prompt) > 20:
                return False, "Excessive capitalization detected"

        # Passed all checks
        return True, None

    def filter_prompt(self, prompt: str, replacement: str = "[FILTERED]") -> str:
        """
        Filter banned content from a prompt instead of blocking it entirely.

        Args:
            prompt: The prompt to filter
            replacement: Text to replace banned keywords with

        Returns:
            str: Filtered prompt
        """
        if not self.enabled:
            return prompt

        filtered = prompt
        for keyword in self.banned_keywords:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            filtered = pattern.sub(replacement, filtered)

        return filtered

    def add_keyword(self, keyword: str):
        """
        Add a keyword to the banned list at runtime.

        Args:
            keyword: Keyword to ban
        """
        keyword_lower = keyword.lower()
        if keyword_lower not in self.banned_keywords:
            self.banned_keywords.append(keyword_lower)
            print(f"Added banned keyword: '{keyword}'")

    def remove_keyword(self, keyword: str):
        """
        Remove a keyword from the banned list.

        Args:
            keyword: Keyword to unban
        """
        keyword_lower = keyword.lower()
        if keyword_lower in self.banned_keywords:
            self.banned_keywords.remove(keyword_lower)
            print(f"Removed banned keyword: '{keyword}'")

    def get_banned_keywords(self) -> List[str]:
        """Get the current list of banned keywords."""
        return self.banned_keywords.copy()

    def enable(self):
        """Enable safety filtering."""
        self.enabled = True
        print("ComplianceGate enabled")

    def disable(self):
        """Disable safety filtering."""
        self.enabled = False
        print("ComplianceGate disabled")


# Singleton instance for easy access
_default_gate = None


def get_default_gate() -> ComplianceGate:
    """Get the default global compliance gate instance."""
    global _default_gate
    if _default_gate is None:
        _default_gate = ComplianceGate()
    return _default_gate


if __name__ == "__main__":
    # Test compliance gate
    gate = ComplianceGate(enable_safety=True)

    test_prompts = [
        "A beautiful sunset over mountains",
        "A violent scene with gore",
        "A peaceful garden with flowers",
        "NSFW content example"
    ]

    print("Testing compliance gate:\n")
    for prompt in test_prompts:
        is_safe, reason = gate.check_prompt(prompt)
        status = "✓ PASS" if is_safe else "✗ BLOCK"
        print(f"{status}: {prompt}")
        if reason:
            print(f"  Reason: {reason}")

    print("\n--- Testing with safety disabled ---")
    gate.disable()
    for prompt in test_prompts:
        is_safe, reason = gate.check_prompt(prompt)
        status = "✓ PASS" if is_safe else "✗ BLOCK"
        print(f"{status}: {prompt}")
