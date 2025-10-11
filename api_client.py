"""
API Client - Handles all API requests with rate limiting protection
"""
import time
import random
import json
import re
import requests
from config import (
    BASE_URL, HEADERS, 
    RETRY_BASE_DELAY, MAX_RETRIES
)


def fetch_submissions(page=1, per_page=10):
    """
    Fetch list of submissions from API
    This is lightweight - usually doesn't get rate limited
    """
    url = f"{BASE_URL}/submissions?page={page}&per_page={per_page}&evaluated=0&search=&sort_order=D&sort_by=submission_time&filters=%5C{{%5C}}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("submission", [])


def fetch_submission_details(attempt_id):
    """
    Fetch details for a specific submission with retry logic
    
    THIS is the endpoint that gets rate limited!
    - Called once per submission (many times per batch)
    - Has heavy retry logic with exponential backoff
    """
    url = f"{BASE_URL}/assignment/pasttest/{attempt_id}"
    
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(url, headers=HEADERS, timeout=30)
            res.raise_for_status()
            return res.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited - show ALL details from response
                print(f"\n{'='*60}")
                print(f"⚠️  RATE LIMITED (429 Error)")
                print(f"{'='*60}")
                print(f"URL: {url}")
                print(f"Status Code: {e.response.status_code}")
                
                # Check for Retry-After header
                retry_after = e.response.headers.get('Retry-After')
                if retry_after:
                    print(f"🕐 Retry-After Header: {retry_after} seconds")
                
                # Show all relevant headers
                print(f"\n📋 Response Headers:")
                for key, value in e.response.headers.items():
                    if key.lower() in ['retry-after', 'x-ratelimit-limit', 'x-ratelimit-remaining', 
                                       'x-ratelimit-reset', 'x-rate-limit-limit', 'x-rate-limit-remaining']:
                        print(f"   {key}: {value}")
                
                # Try to parse response body for wait time
                wait_minutes = None
                try:
                    response_body = e.response.text
                    if response_body:
                        print(f"\n📄 Response Body:")
                        print(f"   {response_body[:500]}")  # First 500 chars
                        
                        # Try to parse JSON response
                        try:
                            response_json = json.loads(response_body)
                            message = response_json.get("message", "")
                            
                            # Extract minutes from message like "Try after 2.82 minutes"
                            match = re.search(r'after\s+([\d.]+)\s+minutes?', message, re.IGNORECASE)
                            if match:
                                wait_minutes = float(match.group(1))
                                print(f"\n🕐 Server says: Wait {wait_minutes} minutes")
                        except:
                            pass
                except:
                    pass
                
                # Calculate wait time (priority: message > Retry-After > exponential backoff)
                if wait_minutes:
                    # Use the exact time from server message, add 5s buffer
                    wait_time = int(wait_minutes * 60) + 5
                    print(f"   Using server's wait time: {wait_time}s ({wait_minutes:.2f} minutes + 5s buffer)")
                elif retry_after and retry_after.isdigit():
                    wait_time = int(retry_after) + random.randint(2, 5)
                    print(f"   Using Retry-After header: {wait_time}s")
                else:
                    wait_time = (attempt + 1) * RETRY_BASE_DELAY + random.randint(5, 15)
                    print(f"   Using exponential backoff: {wait_time}s")
                
                print(f"\n⏳ Waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}...")
                print(f"{'='*60}\n")
                time.sleep(wait_time)
            else:
                raise
                
        except requests.exceptions.Timeout:
            print(f"⏱️  Request timed out, retrying ({attempt + 1}/{MAX_RETRIES})...")
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

