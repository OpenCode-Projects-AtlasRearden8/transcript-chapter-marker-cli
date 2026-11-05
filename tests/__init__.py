"""Make the tests package importable and share the fixture path helper."""

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
