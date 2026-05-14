import os
from pathlib import Path


class Greeter:
    """Say hello."""

    prefix = "hello"

    def greet(self, name: str) -> str:
        """Return a greeting."""
        return f"{self.prefix} {name}".strip()


def helper(value: str) -> str:
    """Normalize a value."""
    return Path(value).name.lower()
