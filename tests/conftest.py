"""Pytest configuration and shared fixtures."""

import contextlib
import glob
import os


def pytest_sessionfinish(session, exitstatus):
    """Clean up temporary database files after test session."""
    for memdb_file in glob.glob("memdb*"):
        with contextlib.suppress(OSError):
            os.remove(memdb_file)
