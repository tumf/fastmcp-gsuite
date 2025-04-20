import logging

from . import auth_helper

logger = logging.getLogger(__name__)

# Account information cache
_account_info_cache = None


def get_user_id_description() -> str:
    """Generates a description for the user_id parameter based on available accounts."""
    global _account_info_cache
    if _account_info_cache is None:
        try:
            _account_info_cache = auth_helper.get_account_info()
            if not _account_info_cache:
                logger.warning("No accounts found in accounts file. User ID description will be generic.")
                return "The EMAIL of the Google account to use."
        except Exception as e:
            logger.error(f"Failed to load account info for user ID description: {e}")
            return "The EMAIL of the Google account to use (Error loading account list)."

    desc = [f"{acc.email} ({acc.account_type})" for acc in _account_info_cache]
    return f"The EMAIL of the Google account. Choose from: {', '.join(desc)}"
