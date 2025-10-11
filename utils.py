"""
Utility functions - delays, waiting, etc.
"""
import time
import random
from config import (
    MIN_DELAY_BETWEEN_REQUESTS,
    MAX_DELAY_BETWEEN_REQUESTS,
    MIN_DELAY_BETWEEN_BATCHES,
    MAX_DELAY_BETWEEN_BATCHES
)


def wait_between_requests():
    """Wait a random time between requests (looks more human)"""
    delay = random.uniform(MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS)
    print(f"⏳ Waiting {delay:.1f}s before next submission...")
    time.sleep(delay)


def wait_between_batches():
    """Wait a longer random time between batches"""
    delay = random.uniform(MIN_DELAY_BETWEEN_BATCHES, MAX_DELAY_BETWEEN_BATCHES)
    print(f"⏳ Waiting {delay:.1f}s before next batch...")
    time.sleep(delay)


def wait_with_countdown(minutes):
    """
    Wait with a countdown timer
    Shows progress every minute
    """
    wait_seconds = minutes * 60
    print(f"\n⏳ Waiting {minutes} minutes...")
    
    for remaining in range(wait_seconds, 0, -60):
        mins = remaining // 60
        print(f"   {mins} minutes remaining...", end='\r')
        time.sleep(60)
    
    print("\n✅ Wait complete!")

