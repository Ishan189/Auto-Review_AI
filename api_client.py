"""
API Client - Handles all API requests with rate limiting protection
"""
import time
import random
import re
import requests
from config import (
    BASE_URL, HEADERS, 
    RETRY_BASE_DELAY, MAX_RETRIES
)


def _parse_retry_wait(response):
    """Parse wait time (in seconds) from a 429 response. Returns None if unparseable."""
    try:
        msg = response.json().get("message", "")
        match = re.search(r'after\s+([\d.]+)\s+minutes?', msg, re.IGNORECASE)
        if match:
            return int(float(match.group(1)) * 60)
    except Exception:
        pass
    retry_after = response.headers.get("Retry-After")
    if retry_after and retry_after.isdigit():
        return int(retry_after)
    return None


def _extract_total_count(data):
    """
    Best-effort extraction of the server-reported total submission count
    from a paginated response. Different LMS APIs use different field names,
    so we check the common ones and return None if nothing matches.
    """
    if not isinstance(data, dict):
        return None
    # Common top-level keys
    for key in ("total", "total_count", "totalCount", "count",
                "total_records", "totalRecords", "total_results"):
        value = data.get(key)
        if isinstance(value, int) and value >= 0:
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    # Sometimes nested under 'pagination' / 'meta'
    for container_key in ("pagination", "meta", "paging"):
        container = data.get(container_key)
        if isinstance(container, dict):
            nested = _extract_total_count(container)
            if nested is not None:
                return nested
    return None


def fetch_submissions(page=1, per_page=50, days_back=30, return_total=False):
    """
    Fetch list of submissions from API with retry logic for rate limits.
    Uses server-side date filtering to limit results.

    Args:
        page: 1-based page index
        per_page: page size
        days_back: how many days back to filter
        return_total: when True, returns (submissions, total_count_or_None)
                      so callers can stop paginating once all records are seen.
                      When False (default, for backwards compatibility),
                      returns just the list of submissions.
    """
    end_date = int(time.time())
    start_date = end_date - (days_back * 24 * 3600)
    url = (f"{BASE_URL}/submissions?page={page}&per_page={per_page}&evaluated=0"
           f"&search=&sort_order=D&sort_by=submission_time"
           f"&start_date={start_date}&end_date={end_date}"
           f"&filters=%5C{{%5C}}")
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            submissions = data.get("submission", []) or []
            if return_total:
                return submissions, _extract_total_count(data)
            return submissions
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = _parse_retry_wait(e.response) or RETRY_BASE_DELAY * (attempt + 1)
                wait += random.randint(2, 10)
                print(f"\n   ⚠️  Rate limited on page {page}, waiting {wait}s (retry {attempt+1}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Failed to fetch submissions page {page} after {MAX_RETRIES} retries")


def fetch_submission_details(attempt_id):
    """
    Fetch details for a specific submission with retry logic
    """
    url = f"{BASE_URL}/assignment/pasttest/{attempt_id}"
    
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, headers=HEADERS, timeout=30)
            res.raise_for_status()
            return res.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = _parse_retry_wait(e.response) or (attempt + 1) * RETRY_BASE_DELAY
                wait += random.randint(2, 10)
                print(f"   ⚠️  Rate limited, waiting {wait}s (retry {attempt+1}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise
                
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout, retrying ({attempt+1}/{MAX_RETRIES})...")
            time.sleep(5)
    
    raise Exception(f"Failed to fetch details for attempt {attempt_id} after {MAX_RETRIES} retries")


def test_api_availability():
    """
    Test if API is accessible and not rate-limited
    
    Tests BOTH endpoints:
    1. fetch_submissions() - lightweight
    2. fetch_submission_details() - HEAVY (this is what gets blocked!)
    
    Returns: (success: bool, error_message: str or None, wait_minutes: float or None)
    """
    try:
        # First test: get list of submissions (usually works)
        submissions = fetch_submissions(page=1, per_page=1)
        
        if not submissions:
            return True, None, None  # No submissions to test, assume OK
        
        # Second test: try to get details for first submission
        # THIS is the endpoint that actually gets rate limited!
        first_attempt_id = submissions[0]["attempt_id"]
        
        url = f"{BASE_URL}/assignment/pasttest/{first_attempt_id}"
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        return True, None, None
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            # Show detailed rate limit info
            print(f"\n{'='*60}")
            print(f"⚠️  RATE LIMITED (429 Error) - During API Test")
            print(f"{'='*60}")
            print(f"Status Code: {e.response.status_code}")
            
            # Check for Retry-After header
            retry_after = e.response.headers.get('Retry-After')
            if retry_after:
                print(f"🕐 Server says retry after: {retry_after} seconds")
            
            # Show rate limit headers
            print(f"\n📋 Rate Limit Info:")
            for key, value in e.response.headers.items():
                if 'limit' in key.lower() or 'retry' in key.lower():
                    print(f"   {key}: {value}")
            
            # Show and parse response body for wait time
            wait_minutes = None
            try:
                response_body = e.response.text
                if response_body:
                    print(f"\n📄 Response Body:")
                    print(f"   {response_body[:500]}")
                    
                    # Try to extract wait time from message
                    try:
                        response_json = json.loads(response_body)
                        message = response_json.get("message", "")
                        
                        # Extract minutes from message like "Try after 2.82 minutes"
                        match = re.search(r'after\s+([\d.]+)\s+minutes?', message, re.IGNORECASE)
                        if match:
                            wait_minutes = float(match.group(1))
                            print(f"\n💡 API says you need to wait: {wait_minutes} minutes ({int(wait_minutes * 60)}s)")
                    except:
                        pass
            except:
                pass
            
            print(f"{'='*60}\n")
            return False, "rate_limited", wait_minutes
        else:
            return False, str(e), None
    except Exception as e:
        return False, str(e), None

