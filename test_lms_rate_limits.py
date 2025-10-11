"""
LMS API Rate Limit Testing Script
Tests all 3 LMS API endpoints separately to find their rate limits
"""
import time
import requests
from config import BASE_URL, HEADERS
from api_client import fetch_submissions, fetch_submission_details
from submitter import submit_marks_and_feedback

print("="*70)
print("🧪 LMS API RATE LIMIT TESTING")
print("="*70)
print("\nThis script will test each LMS API endpoint to find rate limits.")
print("It will stop automatically when rate limited (429 error).\n")

input("Press Enter to start testing... (Ctrl+C to cancel)")

# ============================================================================
# TEST 1: fetch_submissions (List submissions)
# ============================================================================
print("\n" + "="*70)
print("TEST 1: fetch_submissions() - List Submissions API")
print("="*70)
print("Testing how many requests/min before rate limit...\n")

test1_start = time.time()
test1_requests = 0
test1_rate_limited = False

try:
    for i in range(100):  # Try up to 100 requests
        try:
            print(f"Request {i+1}...", end=" ")
            submissions = fetch_submissions(page=1, per_page=5)
            test1_requests += 1
            elapsed = time.time() - test1_start
            rpm = (test1_requests / elapsed) * 60
            print(f"✅ Success | Total: {test1_requests} | Rate: {rpm:.1f} req/min")
            time.sleep(0.5)  # Small delay between requests
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                test1_rate_limited = True
                elapsed = time.time() - test1_start
                rpm = (test1_requests / elapsed) * 60
                print(f"\n❌ RATE LIMITED after {test1_requests} requests in {elapsed:.1f}s")
                print(f"📊 Rate: {rpm:.1f} requests/min")
                break
            else:
                print(f"❌ Error: {e}")
                break
except KeyboardInterrupt:
    print("\n⏸️  Test interrupted by user")

test1_elapsed = time.time() - test1_start
test1_rpm = (test1_requests / test1_elapsed) * 60 if test1_elapsed > 0 else 0

print(f"\n📈 TEST 1 RESULTS:")
print(f"   Requests: {test1_requests}")
print(f"   Duration: {test1_elapsed:.1f}s")
print(f"   Average Rate: {test1_rpm:.1f} req/min")
print(f"   Rate Limited: {'Yes' if test1_rate_limited else 'No'}")

# Wait before next test
if test1_rate_limited:
    print("\n⏳ Waiting 60 seconds before next test to avoid rate limit...")
    time.sleep(60)
else:
    print("\n⏳ Waiting 10 seconds before next test...")
    time.sleep(10)

# ============================================================================
# TEST 2: fetch_submission_details (Get individual submission)
# ============================================================================
print("\n" + "="*70)
print("TEST 2: fetch_submission_details() - Individual Submission API")
print("="*70)
print("Testing how many requests/min before rate limit...\n")

# First, get a valid submission ID
print("Getting a test submission ID...")
try:
    test_submissions = fetch_submissions(page=1, per_page=1)
    if not test_submissions:
        print("❌ No submissions available for testing. Skipping TEST 2.")
        test2_requests = 0
        test2_elapsed = 0
        test2_rpm = 0
        test2_rate_limited = False
    else:
        test_submission_id = test_submissions[0]['id']
        print(f"✅ Using submission ID: {test_submission_id}\n")
        
        test2_start = time.time()
        test2_requests = 0
        test2_rate_limited = False
        
        try:
            for i in range(100):  # Try up to 100 requests
                try:
                    print(f"Request {i+1}...", end=" ")
                    details = fetch_submission_details(test_submission_id)
                    test2_requests += 1
                    elapsed = time.time() - test2_start
                    rpm = (test2_requests / elapsed) * 60
                    print(f"✅ Success | Total: {test2_requests} | Rate: {rpm:.1f} req/min")
                    time.sleep(0.5)  # Small delay between requests
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        test2_rate_limited = True
                        elapsed = time.time() - test2_start
                        rpm = (test2_requests / elapsed) * 60
                        print(f"\n❌ RATE LIMITED after {test2_requests} requests in {elapsed:.1f}s")
                        print(f"📊 Rate: {rpm:.1f} requests/min")
                        break
                    else:
                        print(f"❌ Error: {e}")
                        break
        except KeyboardInterrupt:
            print("\n⏸️  Test interrupted by user")
        
        test2_elapsed = time.time() - test2_start
        test2_rpm = (test2_requests / test2_elapsed) * 60 if test2_elapsed > 0 else 0
        
        print(f"\n📈 TEST 2 RESULTS:")
        print(f"   Requests: {test2_requests}")
        print(f"   Duration: {test2_elapsed:.1f}s")
        print(f"   Average Rate: {test2_rpm:.1f} req/min")
        print(f"   Rate Limited: {'Yes' if test2_rate_limited else 'No'}")
        
        # Wait before next test
        if test2_rate_limited:
            print("\n⏳ Waiting 60 seconds before next test to avoid rate limit...")
            time.sleep(60)
        else:
            print("\n⏳ Waiting 10 seconds before next test...")
            time.sleep(10)

except Exception as e:
    print(f"❌ Error getting test submission: {e}")
    test2_requests = 0
    test2_elapsed = 0
    test2_rpm = 0
    test2_rate_limited = False

# ============================================================================
# TEST 3: submit_marks_and_feedback (Submit grades)
# ============================================================================
print("\n" + "="*70)
print("TEST 3: submit_marks_and_feedback() - Submit Grades API")
print("="*70)
print("⚠️  WARNING: This will submit test feedback to real submissions!")
print("⚠️  This test is DISABLED by default to avoid polluting data.\n")

user_confirm = input("Type 'YES' to enable this test (or Enter to skip): ")

if user_confirm == 'YES':
    print("\n🚨 TEST 3 ENABLED - Testing submission API rate limit...\n")
    
    # Get a test submission
    print("Getting a test submission ID...")
    try:
        test_submissions = fetch_submissions(page=1, per_page=1)
        if not test_submissions:
            print("❌ No submissions available for testing. Skipping TEST 3.")
            test3_requests = 0
            test3_elapsed = 0
            test3_rpm = 0
            test3_rate_limited = False
        else:
            test_submission_id = test_submissions[0]['id']
            print(f"✅ Using submission ID: {test_submission_id}\n")
            
            test3_start = time.time()
            test3_requests = 0
            test3_rate_limited = False
            
            try:
                for i in range(50):  # Try up to 50 requests (fewer to avoid spam)
                    try:
                        print(f"Request {i+1}...", end=" ")
                        # Submit test feedback with incrementing counter
                        test_feedback = f"[TEST {i+1}] Rate limit test - please ignore."
                        test_marks = 0
                        
                        submit_marks_and_feedback(
                            test_submission_id, 
                            test_marks, 
                            test_feedback
                        )
                        
                        test3_requests += 1
                        elapsed = time.time() - test3_start
                        rpm = (test3_requests / elapsed) * 60
                        print(f"✅ Success | Total: {test3_requests} | Rate: {rpm:.1f} req/min")
                        time.sleep(1)  # Longer delay for submission API
                    except requests.exceptions.HTTPError as e:
                        if e.response.status_code == 429:
                            test3_rate_limited = True
                            elapsed = time.time() - test3_start
                            rpm = (test3_requests / elapsed) * 60
                            print(f"\n❌ RATE LIMITED after {test3_requests} requests in {elapsed:.1f}s")
                            print(f"📊 Rate: {rpm:.1f} requests/min")
                            break
                        else:
                            print(f"❌ Error: {e}")
                            break
            except KeyboardInterrupt:
                print("\n⏸️  Test interrupted by user")
            
            test3_elapsed = time.time() - test3_start
            test3_rpm = (test3_requests / test3_elapsed) * 60 if test3_elapsed > 0 else 0
            
            print(f"\n📈 TEST 3 RESULTS:")
            print(f"   Requests: {test3_requests}")
            print(f"   Duration: {test3_elapsed:.1f}s")
            print(f"   Average Rate: {test3_rpm:.1f} req/min")
            print(f"   Rate Limited: {'Yes' if test3_rate_limited else 'No'}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        test3_requests = 0
        test3_elapsed = 0
        test3_rpm = 0
        test3_rate_limited = False
else:
    print("✅ TEST 3 SKIPPED (to avoid submitting test data)")
    test3_requests = 0
    test3_elapsed = 0
    test3_rpm = 0
    test3_rate_limited = False

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*70)
print("📊 FINAL SUMMARY - LMS API RATE LIMITS")
print("="*70)

print("\n┌─────────────────────────────────────────────────────────────┐")
print("│ API ENDPOINT              │ Requests │ Rate Limit Hit │ RPM  │")
print("├─────────────────────────────────────────────────────────────┤")
print(f"│ 1. List Submissions       │ {test1_requests:8} │ {'Yes' if test1_rate_limited else 'No ':^14} │ {test1_rpm:4.1f} │")
print(f"│ 2. Get Submission Details │ {test2_requests:8} │ {'Yes' if test2_rate_limited else 'No ':^14} │ {test2_rpm:4.1f} │")
print(f"│ 3. Submit Grades          │ {test3_requests:8} │ {'Yes' if test3_rate_limited else 'No ':^14} │ {test3_rpm:4.1f} │")
print("└─────────────────────────────────────────────────────────────┘")

print("\n💡 RECOMMENDATIONS:")
print("   Based on the test results:")

if test1_rate_limited:
    safe_rpm_1 = test1_rpm * 0.7
    print(f"   • List Submissions: Stay under {safe_rpm_1:.0f} req/min (tested max: {test1_rpm:.1f})")
else:
    print(f"   • List Submissions: No limit found (tested up to {test1_rpm:.1f} req/min)")

if test2_rate_limited:
    safe_rpm_2 = test2_rpm * 0.7
    print(f"   • Get Details: Stay under {safe_rpm_2:.0f} req/min (tested max: {test2_rpm:.1f})")
else:
    print(f"   • Get Details: No limit found (tested up to {test2_rpm:.1f} req/min)")

if test3_rate_limited:
    safe_rpm_3 = test3_rpm * 0.7
    print(f"   • Submit Grades: Stay under {safe_rpm_3:.0f} req/min (tested max: {test3_rpm:.1f})")
elif test3_requests > 0:
    print(f"   • Submit Grades: No limit found (tested up to {test3_rpm:.1f} req/min)")
else:
    print("   • Submit Grades: Not tested")

print("\n✅ Testing complete!")

