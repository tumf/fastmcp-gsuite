import os

import pytest


def pytest_configure(config):
    """Register e2e marker"""
    config.addinivalue_line("markers", "e2e: mark a test as an end-to-end test")


def pytest_addoption(parser):
    """Add e2e command line option"""
    parser.addoption(
        "--run-e2e", action="store_true", default=False, help="Run e2e tests"
    )


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests unless --run-e2e is specified"""
    if config.getoption("--run-e2e"):
        # --run-e2e given in cli: do not skip e2e tests
        return

    skip_e2e = pytest.mark.skip(reason="Need --run-e2e option to run")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip_e2e)


@pytest.fixture(scope="session", autouse=True)
def check_env_vars():
    """Check if required environment variables are set for e2e tests"""
    required_vars = [
        "GSUITE_CREDENTIALS_JSON",
        "GOOGLE_ACCOUNT_EMAIL",
        "GOOGLE_PROJECT_ID",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
    ]

    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        pytest.skip(
            f"Missing required environment variables for e2e tests: {', '.join(missing_vars)}"
        )
