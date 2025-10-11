"""
Auto Review - Assignment Downloader with AI Review
Simple script to download and review student assignments with rate limiting protection

Usage:
    python3 auto_review.py
    
Configuration:
    Edit .env file to adjust settings (see CONFIG.md for guide)
"""

import os
from config import BATCH_SIZE, MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS
from config import MIN_DELAY_BETWEEN_BATCHES, MAX_DELAY_BETWEEN_BATCHES, MAX_RETRIES, GEMINI_API_KEY
from api_client import fetch_submissions, fetch_submission_details, test_api_availability
from downloader import download_submission_files
from utils import wait_between_requests, wait_between_batches, wait_with_countdown
from reviewer import review_assignment, format_feedback_for_submission
from submitter import submit_marks_and_feedback


def print_header():
    """Print welcome header with current settings"""
    print("=" * 60)
    print("🤖 Auto Review - Assignment Downloader with AI")
    print("=" * 60)
    print(f"\n⚙️  Current Configuration:")
    print(f"   Batch Size: {BATCH_SIZE} submissions")
    print(f"   Delay Between Requests: {MIN_DELAY_BETWEEN_REQUESTS}-{MAX_DELAY_BETWEEN_REQUESTS}s")
    print(f"   Delay Between Batches: {MIN_DELAY_BETWEEN_BATCHES}-{MAX_DELAY_BETWEEN_BATCHES}s")
    print(f"   Max Retries: {MAX_RETRIES}")
    
    # Show AI status
    if GEMINI_API_KEY:
        print(f"   🤖 AI Review: ✅ Enabled (Gemini API)")
    else:
        print(f"   🤖 AI Review: ⚠️ Disabled (No API key)")
    
    print(f"   💡 Adjust settings in your .env file (see CONFIG.md)")
    print("\n" + "=" * 60 + "\n")


def check_api_status():
    """
    Check if API is accessible
    Returns: True if accessible, False if blocked
    """
    print("🔍 Testing API availability...")
    
    success, error, wait_minutes = test_api_availability()
    
    if success:
        print("✅ API is accessible!\n")
        return True
    
    if error == "rate_limited":
        print("\n❌ You are currently rate-limited!")
        
        # Use the exact wait time from API if available
        if wait_minutes:
            wait_mins = int(wait_minutes) + 1  # Round up and add 1 min buffer
            print(f"⏰ Server says to wait: {wait_minutes:.2f} minutes")
            print(f"💡 Auto-waiting {wait_mins} minutes...\n")
        else:
            # Fallback if we couldn't parse the wait time
            wait_mins = 20
            print("⏰ Recommended wait: 15-30 minutes")
            print(f"💡 Auto-waiting {wait_mins} minutes to be safe...\n")
        
        # Automatically wait (no user input)
        wait_with_countdown(wait_mins)
        
        # Retry after waiting
        print("\n🔄 Retrying API connection...")
        success, _, _ = test_api_availability()
        if success:
            print("✅ API is now accessible!")
            return True
        else:
            print("❌ Still blocked. Exiting - please try again later.")
            return False
    else:
        print(f"❌ Error: {error}")
        return False


def process_submission(submission, index, total, auto_submit=False):
    """
    Process a single submission - fetch details, download, review, and optionally submit
    
    Args:
        submission: Submission data
        index: Current index
        total: Total count
        auto_submit: If True, automatically submit marks and feedback
    """
    attempt_id = submission["attempt_id"]
    student_name = submission.get("name", "Unknown")
    assignment_name = submission.get("assessment_name", "Unknown Assignment")
    
    print(f"\n📚 [{index}] {student_name} - {assignment_name}")
    print(f"   Attempt ID: {attempt_id}")
    
    try:
        # Step 1: Fetch details
        print(f"   🔍 Fetching details...")
        details = fetch_submission_details(attempt_id)
        
        # Step 2: Download files
        print(f"   📥 Downloading files...")
        files = download_submission_files(details)
        
        if not files:
            print(f"   ⚠️ No files to review")
            return True
        
        print(f"   ✅ Downloaded {len(files)} file(s)")
        
        # Step 3: Review first file (usually the main submission)
        main_file = files[0]
        print(f"   🤖 Reviewing {os.path.basename(main_file)}...")
        
        review_result = review_assignment(main_file)
        
        # Step 4: Show review result
        if not review_result['is_valid_format']:
            print(f"   {review_result['feedback']}")
        elif not review_result['can_review']:
            print(f"   {review_result['feedback']}")
        else:
            print(f"   ✅ Review Complete!")
            if review_result['suggested_marks']:
                print(f"   📊 Score: {review_result['suggested_marks']}/100")
        
        # Step 5: Submit if enabled
        if auto_submit and review_result['can_review']:
            marks = review_result['suggested_marks'] or 0
            feedback_html = format_feedback_for_submission(review_result)
            
            # Show what we're submitting
            print(f"\n   📋 SUBMISSION DETAILS:")
            print(f"   Student: {student_name}")
            print(f"   Assignment: {assignment_name}")
            print(f"   Score: {marks}/100")
            
            # Show clean feedback (without HTML tags)
            clean_feedback = review_result['review']
            if '=== SCORE ===' in clean_feedback:
                clean_feedback = clean_feedback.split('=== SCORE ===')[0].strip()
            if '=== REVIEW ===' in clean_feedback:
                clean_feedback = clean_feedback.split('=== REVIEW ===')[1].strip()
            
            char_count = len(clean_feedback)
            print(f"\n   💬 FEEDBACK ({char_count} chars):")
            print(f"   " + "="*50)
            
            # Print feedback with indentation
            for line in clean_feedback.split('\n'):
                if line.strip():
                    print(f"   {line}")
            print(f"   " + "="*50)
            
            success, response = submit_marks_and_feedback(details, marks, feedback_html)
            
            if success:
                # Delete downloaded files after successful submission
                print(f"\n   🗑️  Cleaning up downloaded files...")
                for file_path in files:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            print(f"   ✅ Deleted: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"   ⚠️  Could not delete {os.path.basename(file_path)}: {e}")
            else:
                print(f"   ⚠️  Submission failed - files kept for manual review")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def process_batch(submissions, start_index, auto_submit=False):
    """Process a batch of submissions"""
    print(f"\nProcessing {len(submissions)} submissions in this batch...\n")
    
    for idx, submission in enumerate(submissions, 1):
        global_idx = start_index + idx
        success = process_submission(submission, global_idx, start_index + len(submissions), auto_submit)
        
        print("-" * 50)
        
        # Wait between submissions (except after the last one)
        if idx < len(submissions):
            wait_between_requests()
    
    return len(submissions)


def main():
    """Main function - fully automated processing"""
    print_header()
    
    # Check if API is accessible
    if not check_api_status():
        return
    
    # Check if AI is configured
    if not GEMINI_API_KEY:
        print("❌ AI not configured - GEMINI_API_KEY missing in .env")
        print("   Cannot proceed without AI review capability")
        return
    
    print("🤖 FULLY AUTOMATED MODE")
    print("   • Process 1 submission at a time")
    print("   • Download → Review → Submit → Delete")
    print("   • No user input required")
    print("   • Continues until all submissions done\n")
    
    # Fetch all pending submissions one at a time
    total_processed = 0
    total_failed = 0
    page = 1
    
    while True:
        # Fetch ONE submission at a time
        print(f"\n{'='*60}")
        print(f"🔍 Checking for submission #{total_processed + 1}...")
        print(f"{'='*60}")
        
        submissions = fetch_submissions(page=page, per_page=1)
        
        if not submissions:
            print("✅ No more submissions to process!")
            break
        
        submission = submissions[0]
        
        # Process this single submission
        success = process_submission(submission, total_processed + 1, total_processed + 1, auto_submit=True)
        
        if success:
            total_processed += 1
        else:
            total_failed += 1
        
        print(f"\n📊 Progress: {total_processed} completed, {total_failed} failed")
        print("-" * 60)
        
        # Wait before next submission (rate limiting)
        wait_between_requests()
        
        page += 1
    
    print(f"\n{'='*60}")
    print(f"🎉 AUTOMATION COMPLETE!")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {total_processed}")
    print(f"❌ Failed: {total_failed}")
    print(f"📊 Total: {total_processed + total_failed}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  Interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise
