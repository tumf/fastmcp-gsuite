# Change: Fix async test warnings in make test

## Why

Running `make test` produces multiple RuntimeWarning and DeprecationWarning messages for async test methods in unit tests. The root cause is that three test files (`test_calendar_tools.py`, `test_gmail_drive_tools.py`, `test_gmail_tools.py`) use `unittest.TestCase` with `async def` test methods, which is not supported. Python's `unittest.TestCase` does not natively handle async test methods, causing coroutines to never be awaited.

## What Changes

- Update `test_calendar_tools.py` to use `unittest.IsolatedAsyncioTestCase` instead of `unittest.TestCase`
- Update `test_gmail_drive_tools.py` to use `unittest.IsolatedAsyncioTestCase` instead of `unittest.TestCase`
- Update `test_gmail_tools.py` to use `unittest.IsolatedAsyncioTestCase` instead of `unittest.TestCase`

## Impact

- Affected specs: None (no spec changes needed)
- Affected code: `tests/unit/test_calendar_tools.py`, `tests/unit/test_gmail_drive_tools.py`, `tests/unit/test_gmail_tools.py`
- Risk: Low - only changing the base class for test classes
- The fix follows the same pattern already used in `test_drive_tools.py` which works correctly
