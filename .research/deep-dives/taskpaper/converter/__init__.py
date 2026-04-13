"""
OmniFocus JSON <-> TaskPaper bidirectional converter.

Two modes:
  - full: Every field included, lossless round-trip
  - llm:  Only fields useful for LLM reasoning, optimised for token efficiency
"""

from .json_to_taskpaper import json_to_taskpaper, Mode
from .taskpaper_to_json import taskpaper_to_json

__all__ = ["json_to_taskpaper", "taskpaper_to_json", "Mode"]
