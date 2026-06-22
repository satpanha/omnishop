"""
Telegram Mini App initData validation.

Implements the official validation protocol:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

Steps:
  1. Parse the initData query string
  2. Extract the 'hash' parameter
  3. Sort remaining key=value pairs alphabetically and join with \\n
  4. secret_key = HMAC-SHA256("WebAppData", bot_token)
  5. calculated_hash = HMAC-SHA256(secret_key, data_check_string)
  6. Compare calculated_hash with provided hash
  7. Verify auth_date is within 24 hours
  8. Return the parsed user dict on success
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qs, unquote

from fastapi import HTTPException, status

# Maximum allowed age of auth_date (24 hours)
MAX_AUTH_AGE_SECONDS = 86400


def validate_init_data(init_data: str, bot_token: str) -> dict:
    """
    Validate Telegram Mini App initData and return the user data dict.

    Args:
        init_data: Raw initData query string from the Telegram Mini App.
        bot_token: The bot's secret token.

    Returns:
        Parsed user data dictionary from the 'user' field.

    Raises:
        HTTPException(401): If validation fails for any reason.
    """
    try:
        # Step 1: Parse query string
        parsed = parse_qs(init_data, keep_blank_values=True)

        # Flatten: parse_qs returns lists, take first value of each
        data = {k: v[0] for k, v in parsed.items()}

        # Step 2: Extract and remove hash
        received_hash = data.pop("hash", None)
        if not received_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing hash in initData",
            )

        # Step 3: Build data_check_string (sorted key=value pairs joined by \n)
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(data.items())
        )

        # Step 4: Create secret key = HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        # Step 5: Calculate hash = HMAC-SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        # Step 6: Compare hashes (constant-time comparison)
        if not hmac.compare_digest(calculated_hash, received_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid initData hash",
            )

        # Step 7: Check auth_date freshness
        auth_date_str = data.get("auth_date")
        if not auth_date_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing auth_date in initData",
            )

        auth_date = int(auth_date_str)
        current_time = int(time.time())
        if current_time - auth_date > MAX_AUTH_AGE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="initData has expired (older than 24 hours)",
            )

        # Step 8: Parse and return user data
        user_raw = data.get("user")
        if not user_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing user in initData",
            )

        user_data = json.loads(unquote(user_raw))
        return user_data

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"initData validation failed: {exc}",
        ) from exc
