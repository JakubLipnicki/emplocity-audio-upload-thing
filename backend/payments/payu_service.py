# payments/payu_service.py
import json  # For working with JSON data

import requests  # For making HTTP requests
from django.conf import (  # To access Django project settings (PAYU_*, YOUR_APP_BASE_URL)
    settings,
)
from django.core.cache import cache  # For caching the PayU access token

# Unique cache key for storing the PayU access token.
PAYU_ACCESS_TOKEN_CACHE_KEY = (
    "payu_access_token_v3"  # Versioned to avoid potential old cache conflicts
)


def get_payu_access_token():
    """
    Retrieves PayU OAuth access token.
    Tries to get it from Django's cache first. If not found or expired,
    fetches a new token from PayU API and caches it.
    Returns:
        str: The access token, or None if an error occurred.
    """
    cached_token = cache.get(PAYU_ACCESS_TOKEN_CACHE_KEY)
    if cached_token:
        return cached_token  # Return cached token if available and valid.

    client_id = settings.PAYU_OAUTH_CLIENT_ID
    client_secret = settings.PAYU_OAUTH_CLIENT_SECRET
    oauth_url = settings.PAYU_OAUTH_URL

    if not all([client_id, client_secret, oauth_url]):
        print(
            f"PAYU_SERVICE_ERROR: Missing PayU OAuth configuration. Required: PAYU_OAUTH_CLIENT_ID, PAYU_OAUTH_CLIENT_SECRET, PAYU_OAUTH_URL."
        )
        return None

    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    print(f"PAYU_SERVICE_INFO: Requesting new OAuth token from PayU: {oauth_url}")
    try:
        response = requests.post(oauth_url, data=data, headers=headers, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        if not access_token:
            print(
                f"PAYU_SERVICE_ERROR: 'access_token' not found in PayU OAuth response. Response: {token_data}"
            )
            return None

        cache_timeout = expires_in - 300 if expires_in > 300 else expires_in
        cache.set(PAYU_ACCESS_TOKEN_CACHE_KEY, access_token, timeout=cache_timeout)
        print(
            f"PAYU_SERVICE_INFO: Successfully fetched and cached PayU OAuth token. Expires in: {cache_timeout}s"
        )
        return access_token

    except requests.exceptions.HTTPError as e:
        print(
            f"PAYU_SERVICE_ERROR: HTTPError during OAuth token request: {e.response.status_code} - {e.response.text}"
        )
    except requests.exceptions.RequestException as e:
        print(f"PAYU_SERVICE_ERROR: RequestException during OAuth token request: {e}")
    except json.JSONDecodeError as e:  # Handle cases where response is not valid JSON
        print(
            f"PAYU_SERVICE_ERROR: JSONDecodeError during OAuth token request. Response text: {response.text if 'response' in locals() else 'N/A'}. Error: {e}"
        )
    except Exception as e:  # Catch any other unexpected errors
        print(f"PAYU_SERVICE_ERROR: Unexpected error during OAuth token request: {e}")

    return None


def create_payu_order_api_call(order_payload_dict):
    """
    Sends a request to PayU API to create a new order.
    Args:
        order_payload_dict (dict): Dictionary containing the order data compliant with PayU API.
    Returns:
        dict: The JSON response from PayU API, or a dictionary with an 'error' key if failed.
    """
    access_token = get_payu_access_token()
    if not access_token:
        print(
            "PAYU_SERVICE_ERROR: Cannot create PayU order - failed to obtain access token."
        )
        return {
            "error": "Failed to obtain access token",
            "details": "Access token is missing or could not be retrieved.",
        }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",  # OAuth Bearer token.
    }

    api_url = settings.PAYU_API_ORDER_URL  # PayU Order API endpoint from settings.
    if not api_url:
        print("PAYU_SERVICE_ERROR: PAYU_API_ORDER_URL is not configured in settings.")
        return {
            "error": "Configuration error",
            "details": "PayU API Order URL is not set.",
        }

    print(f"PAYU_SERVICE_INFO: Creating order with PayU. URL: {api_url}")
    # For debugging, it's useful to log the payload, but be mindful of sensitive data in production logs.
    # print(f"PAYU_SERVICE_DEBUG: Order payload: {json.dumps(order_payload_dict, indent=2)}")

    try:
        # `allow_redirects=False` is important as PayU might respond with 302 (Found)
        # and the `redirectUri` will be in the 'Location' header.
        response = requests.post(
            api_url,
            json=order_payload_dict,
            headers=headers,
            timeout=15,
            allow_redirects=False,
        )

        print(
            f"PAYU_SERVICE_INFO: Received response from PayU. Status: {response.status_code}"
        )

        # Attempt to parse JSON response regardless of status code, as errors might be in JSON body.
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            # If JSON parsing fails, create a basic error structure.
            # This is especially relevant for 302 responses which might have an empty body.
            response_data = {
                "error_raw_response": response.text[:500]
            }  # Store a snippet of non-JSON response for debugging.
            print(
                f"PAYU_SERVICE_WARNING: PayU response was not valid JSON. Status: {response.status_code}. Snippet: {response.text[:100]}"
            )

        # If PayU responds with a redirect (302), the actual redirect URL is in the 'Location' header.
        # The body might also contain `orderId`.
        if response.status_code == 302 and "Location" in response.headers:
            response_data["redirectUri"] = response.headers["Location"]
            # PayU might also include orderId in the body of a 302, so we keep parsed response_data.

        # Add status code to the response data for easier handling in views.
        response_data["status_code_received_from_payu"] = response.status_code

        if response.status_code not in [
            200,
            201,
            302,
        ]:  # Consider these as "successful" or "redirect" statuses.
            # For other statuses, log as potential errors but still return the data.
            # The view layer will decide how to interpret based on status_code_received_from_payu.
            print(
                f"PAYU_SERVICE_WARNING: PayU returned non-successful/redirect status: {response.status_code}. Response data: {response_data}"
            )

        return response_data

    except (
        requests.exceptions.HTTPError
    ) as e:  # Handles 4xx/5xx from response.raise_for_status() if it were used for all codes
        error_details = e.response.text[:500]  # Get snippet of error response
        try:  # Try to parse error as JSON
            error_details = e.response.json()
        except json.JSONDecodeError:
            pass  # Keep text snippet if not JSON
        print(
            f"PAYU_SERVICE_ERROR: HTTPError during order creation: {e.response.status_code} - Details: {error_details}"
        )
        return {
            "error": "HTTPError",
            "status_code_received_from_payu": e.response.status_code,
            "details": error_details,
        }
    except (
        requests.exceptions.RequestException
    ) as e:  # Catches connection errors, timeouts, etc.
        print(f"PAYU_SERVICE_ERROR: RequestException during order creation: {e}")
        return {"error": "RequestException", "details": str(e)}
    except Exception as e:  # Catch any other unexpected errors
        print(f"PAYU_SERVICE_ERROR: Unexpected error during order creation: {e}")
        return {"error": "UnexpectedError", "details": str(e)}
