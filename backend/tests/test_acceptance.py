"""Asserts the section 9 acceptance checks against the built database.

Run `npm run ingest` first to (re)build db/plantpulse.sqlite.
"""

import sqlite3

import pytest

from app.config import DB_PATH, ROOT_DIR
from app.ingest.acceptance import run_acceptance_checks

pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="run `npm run ingest` first")


@pytest.fixture(scope="module")
def results():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield run_acceptance_checks(conn, ROOT_DIR)
    finally:
        conn.close()


def test_all_checks_pass_or_are_explicitly_deferred(results):
    failed = [r.name for r in results if r.passed is False]
    assert not failed, f"Failed acceptance checks: {failed}"


@pytest.mark.parametrize("index", range(11))
def test_individual_check(results, index):
    check = results[index]
    assert check.passed is not False, f"{check.name}: {check.detail}"
