import pytest


def pytest_configure(config):
    """Register global e2e marker"""
    config.addinivalue_line("markers", "e2e: mark a test as an end-to-end test")
    config.addinivalue_line("markers", "asyncio: mark a test as an asyncio test")


def pytest_addoption(parser):
    """Add e2e command line option"""
    parser.addoption("--run-e2e", action="store_true", default=False, help="Run e2e tests")


def pytest_collection_modifyitems(config, items):
    """Skip e2e tests unless --run-e2e is specified"""
    if config.getoption("--run-e2e"):
        # --run-e2e given in cli: do not skip e2e tests
        return

    # Skip all tests from the e2e directory
    skip_e2e = pytest.mark.skip(reason="Need --run-e2e option to run e2e tests")
    for item in items:
        # Check both the marker and also if the test is in the e2e directory
        if "e2e" in item.keywords or "tests/e2e" in str(item.fspath):
            item.add_marker(skip_e2e)
