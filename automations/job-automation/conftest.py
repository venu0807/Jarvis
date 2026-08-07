"""Pytest config: LLM-bound tests are skipped by default.

They boot a local Ollama server (tailor_resume) and take minutes.
Run them explicitly with:  RUN_LLM_TESTS=1 pytest
"""
import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "llm: needs local Ollama; run with RUN_LLM_TESTS=1")


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_LLM_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="LLM test — set RUN_LLM_TESTS=1 to run")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip)
