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


def process_submission_with_tracking(submission, index, total, auto_submit=False):
    """
    Process a single submission with result tracking
    Returns: (success: bool, result_type: str)
    result_type: 'pdf_graded', 'doc_rejected', 'zip_rejected', 'invalid_format', 'no_files'
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
            print(f"   ⚠️ No files found for this submission")
            
            # Submit feedback about missing files if auto_submit is enabled
            if auto_submit:
                marks = 0
                feedback_html = f"""<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; color: #d32f2f; padding: 15px;">
<p><strong>⚠️ No File Submitted</strong></p>
<p>Hi! I see you submitted this assignment, but <strong>no file was attached</strong>.</p>
<p><strong>What happened:</strong> You may have clicked submit without uploading your assignment file.</p>
<p><strong>What to do:</strong><br>
1. Prepare your assignment as a PDF file<br>
2. Go back to the assignment page<br>
3. Click "Add submission" or "Edit submission"<br>
4. Upload your PDF file<br>
5. Click Submit</p>
<p>Please upload your file to receive a grade. Your work will be automatically reviewed once you submit it!</p>
</div>"""
                
                print(f"\n   📋 SUBMITTING 'NO FILE' FEEDBACK:")
                print(f"   Student: {student_name}")
                print(f"   Assignment: {assignment_name}")
                print(f"   Score: 0/100 (No file uploaded)")
                
                success, response = submit_marks_and_feedback(details, marks, feedback_html)
                
                if success:
                    print(f"   ✅ Feedback submitted!")
                else:
                    print(f"   ⚠️  Failed to submit feedback")
            
            return True, 'no_files'
        
        print(f"   ✅ Downloaded {len(files)} file(s)")
        
        # Step 3: Review first file
        main_file = files[0]
        print(f"   🤖 Reviewing {os.path.basename(main_file)}...")
        
        review_result = review_assignment(main_file, student_name=student_name)
        
        # Determine result type
        file_ext = os.path.splitext(main_file)[1].lower()
        result_type = 'unknown'
        
        if not review_result['is_valid_format']:
            if file_ext in ['.doc', '.docx']:
                result_type = 'doc_rejected'
            elif file_ext == '.zip':
                result_type = 'zip_rejected'
            else:
                result_type = 'invalid_format'
        elif review_result['can_review']:
            result_type = 'pdf_graded'
        
        # Show review result
        if not review_result['is_valid_format']:
            print(f"   {review_result['feedback']}")
        elif not review_result['can_review']:
            print(f"   {review_result['feedback']}")
        else:
            print(f"   ✅ Review Complete!")
            if review_result['suggested_marks']:
                print(f"   📊 Score: {review_result['suggested_marks']}/100")
        
        # Submit feedback
        if auto_submit:
            if not review_result['is_valid_format']:
                marks = 0
                
                # Check if this is an AI review failure - DON'T submit feedback
                if 'AI_REVIEW_FAILED' in review_result['feedback']:
                    print(f"   ❌ AI Review Failed - NOT submitting feedback")
                    print(f"   🔍 Error: {review_result.get('error', 'Unknown error')}")
                    print(f"   🔄 Retries attempted: {review_result.get('retry_count', 0)}")
                    print(f"\n   ⚠️  Script will terminate - manual review required")
                    return False, 'ai_failure'  # Return False to indicate failure
                elif '.doc' in review_result['feedback'].lower():
                    feedback_html = f"""<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; color: #ff9800; padding: 15px;">
<p><strong>📄 Document Format Not Supported</strong></p>
<p>Hi! You submitted a .doc/.docx file, which cannot be automatically reviewed by our system.</p>
<p><strong>Required Format:</strong> Please convert your document to <strong>PDF</strong> format.</p>
<p><strong>How to convert:</strong><br>
1. Open your .doc/.docx file<br>
2. Click "File" → "Save As" or "Export"<br>
3. Choose "PDF" as the format<br>
4. Resubmit the PDF file</p>
<p>Once you resubmit as PDF, your work will be automatically reviewed and graded. Thank you!</p>
</div>"""
                else:
                    feedback_html = f"""<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; color: #d32f2f; padding: 15px;">
<p><strong>⚠️ Invalid File Format</strong></p>
<p>Hi! You submitted a file in an unsupported format.</p>
<p><strong>Issue:</strong> {review_result['feedback']}</p>
<p><strong>Required Format:</strong> Please resubmit as <strong>PDF</strong>.</p>
<p><strong>What to do:</strong><br>
1. Convert your code/solutions to PDF format<br>
2. Make sure all your code is visible and readable<br>
3. Resubmit the assignment</p>
<p>Please resubmit in PDF format to receive a grade. Looking forward to reviewing your work!</p>
</div>"""
                
                print(f"\n   📋 SUBMITTING FORMAT ERROR FEEDBACK:")
                print(f"   Student: {student_name}")
                print(f"   Assignment: {assignment_name}")
                print(f"   Score: 0/100 (Invalid format)")
                
                success, response = submit_marks_and_feedback(details, marks, feedback_html)
                
                if success:
                    print(f"\n   🗑️  Cleaning up invalid file...")
                    for file_path in files:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                print(f"   ✅ Deleted: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"   ⚠️  Could not delete {os.path.basename(file_path)}: {e}")
                
            elif review_result['can_review']:
                marks = review_result['suggested_marks'] or 0
                feedback_html = format_feedback_for_submission(review_result)
                
                print(f"\n   📋 SUBMISSION DETAILS:")
                print(f"   Student: {student_name}")
                print(f"   Assignment: {assignment_name}")
                print(f"   Score: {marks}/100")
                
                clean_feedback = review_result['review']
                if '=== SCORE ===' in clean_feedback:
                    clean_feedback = clean_feedback.split('=== SCORE ===')[0].strip()
                if '=== REVIEW ===' in clean_feedback:
                    clean_feedback = clean_feedback.split('=== REVIEW ===')[1].strip()
                
                char_count = len(clean_feedback)
                word_count = len(clean_feedback.split())
                print(f"\n   💬 FEEDBACK ({char_count} chars, ~{word_count} words):")
                print(f"   " + "="*50)
                
                for line in clean_feedback.split('\n'):
                    if line.strip():
                        print(f"   {line}")
                print(f"   " + "="*50)
                
                success, response = submit_marks_and_feedback(details, marks, feedback_html)
                
                if success:
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
                    return False, result_type
        
        return True, result_type
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, 'error'


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
        
        review_result = review_assignment(main_file, student_name=student_name)
        
        # Step 4: Show review result
        if not review_result['is_valid_format']:
            print(f"   {review_result['feedback']}")
        elif not review_result['can_review']:
            print(f"   {review_result['feedback']}")
        else:
            print(f"   ✅ Review Complete!")
            if review_result['suggested_marks']:
                print(f"   📊 Score: {review_result['suggested_marks']}/100")
        
        # Step 5: Submit feedback (even for invalid formats)
        if auto_submit:
            # For invalid file formats, submit 0 marks with format error message
            if not review_result['is_valid_format']:
                marks = 0
                
                # Check if this is an AI review failure - DON'T submit feedback
                if 'AI_REVIEW_FAILED' in review_result['feedback']:
                    print(f"   ❌ AI Review Failed - NOT submitting feedback")
                    print(f"   🔍 Error: {review_result.get('error', 'Unknown error')}")
                    print(f"   🔄 Retries attempted: {review_result.get('retry_count', 0)}")
                    print(f"\n   ⚠️  Script will terminate - manual review required")
                    return False  # Return False to indicate failure (process_submission returns bool only)
                # Customize message based on file type
                elif '.doc' in review_result['feedback'].lower():
                    feedback_html = f"""<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; color: #ff9800; padding: 15px;">
<p><strong>📄 Document Format Not Supported</strong></p>
<p>Hi! You submitted a .doc/.docx file, which cannot be automatically reviewed by our system.</p>
<p><strong>Required Format:</strong> Please convert your document to <strong>PDF</strong> format.</p>
<p><strong>How to convert:</strong><br>
1. Open your .doc/.docx file<br>
2. Click "File" → "Save As" or "Export"<br>
3. Choose "PDF" as the format<br>
4. Resubmit the PDF file</p>
<p>Once you resubmit as PDF, your work will be automatically reviewed and graded. Thank you!</p>
</div>"""
                else:
                    feedback_html = f"""<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; color: #d32f2f; padding: 15px;">
<p><strong>⚠️ Invalid File Format</strong></p>
<p>Hi! You submitted a file in an unsupported format.</p>
<p><strong>Issue:</strong> {review_result['feedback']}</p>
<p><strong>Required Format:</strong> Please resubmit as <strong>PDF</strong>.</p>
<p><strong>What to do:</strong><br>
1. Convert your code/solutions to PDF format<br>
2. Make sure all your code is visible and readable<br>
3. Resubmit the assignment</p>
<p>Please resubmit in PDF format to receive a grade. Looking forward to reviewing your work!</p>
</div>"""
                
                print(f"\n   📋 SUBMITTING FORMAT ERROR FEEDBACK:")
                print(f"   Student: {student_name}")
                print(f"   Assignment: {assignment_name}")
                print(f"   Score: 0/100 (Invalid format)")
                
                success, response = submit_marks_and_feedback(details, marks, feedback_html)
                
                if success:
                    # Delete the invalid file
                    print(f"\n   🗑️  Cleaning up invalid file...")
                    for file_path in files:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                print(f"   ✅ Deleted: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"   ⚠️  Could not delete {os.path.basename(file_path)}: {e}")
                
            # For valid formats with successful review
            elif review_result['can_review']:
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
    import time
    from datetime import datetime, timedelta
    
    start_time = time.time()
    start_datetime = datetime.now()
    
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
    
    # First, fetch ALL pending submissions to show total count
    print("📊 Fetching all pending submissions...")
    all_submissions = []
    page = 1
    per_page = 10  # Fetch in batches of 50
    
    while True:
        batch = fetch_submissions(page=page, per_page=per_page)
        if not batch:
            break
        all_submissions.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    
    if not all_submissions:
        print("✅ No pending submissions to evaluate!")
        return
    
    # Show total count and summary
    print(f"\n{'='*70}")
    print(f"📋 FOUND {len(all_submissions)} PENDING SUBMISSION(S) TO EVALUATE")
    print(f"{'='*70}")
    print(f"\n📝 Preview (first 10):")
    for i, sub in enumerate(all_submissions[:10], 1):
        name = sub.get("name", "Unknown")
        assignment = sub.get("assessment_name", "N/A")
        print(f"   {i}. {name} - {assignment}")
    
    if len(all_submissions) > 10:
        print(f"   ... and {len(all_submissions) - 10} more")
    
    print(f"\n{'='*70}")
    print(f"🚀 Starting automated processing of {len(all_submissions)} submission(s)...")
    print(f"{'='*70}\n")
    
    # Now process each submission one by one
    total_processed = 0
    total_failed = 0
    total_pdf_graded = 0
    total_invalid_format = 0
    total_doc_files = 0
    total_zip_files = 0
    total_no_files = 0
    total_api_calls = 0  # Track Gemini API usage
    total_lms_api_calls = 0  # Track LMS API calls
    failed_attempts = []
    
    # Time tracking
    submission_times = []
    api_call_times = []
    
    for idx, submission in enumerate(all_submissions, 1):
        submission_start = time.time()
        
        print(f"\n{'='*60}")
        print(f"🔍 Processing submission {idx}/{len(all_submissions)}...")
        print(f"{'='*60}")
        student_name = submission.get("name", "Unknown")
        assignment_name = submission.get("assessment_name", "Unknown")
        
        # Process this single submission
        success, result_type = process_submission_with_tracking(
            submission, idx, len(all_submissions), auto_submit=True
        )
        
        # Track timing
        submission_time = time.time() - submission_start
        submission_times.append(submission_time)
        
        # Track API calls timing
        api_call_times.append(time.time())
        total_lms_api_calls += 2  # fetch_details + submit_marks (minimum)
        
        if success:
            total_processed += 1
            # Track what type of submission it was
            if result_type == 'pdf_graded':
                total_pdf_graded += 1
                total_api_calls += 1  # PDF reviews use Gemini API
            elif result_type == 'doc_rejected':
                total_doc_files += 1
                total_invalid_format += 1
            elif result_type == 'zip_rejected':
                total_zip_files += 1
                total_invalid_format += 1
            elif result_type == 'no_files':
                total_no_files += 1
            elif result_type == 'invalid_format':
                total_invalid_format += 1
        else:
            total_failed += 1
            failed_attempts.append({
                'student': student_name,
                'assignment': assignment_name,
                'reason': 'AI review failed after max retries'
            })
            
            # SOUND ALERT ON FAILURE
            print("\n🔔 ALERT: AI Review Failed!")
            os.system('afplay /System/Library/Sounds/Sosumi.aiff')  # macOS sound
            
            # Terminate script immediately on AI failure
            print(f"\n{'='*70}")
            print("❌ SCRIPT TERMINATED - AI REVIEW FAILURE")
            print(f"{'='*70}")
            print(f"\n📊 Stats before termination:")
            print(f"   Processed: {total_processed}/{len(all_submissions)}")
            print(f"   Successfully graded: {total_pdf_graded}")
            print(f"   Failed on: {student_name} - {assignment_name}")
            print(f"\n💡 What to do:")
            print(f"   1. Check the error message above")
            print(f"   2. Fix the issue (API key, network, etc.)")
            print(f"   3. Re-run the script - it will process remaining submissions")
            print(f"\n📂 Files preserved in assignments/ folder for manual review")
            print(f"{'='*70}\n")
            break  # Terminate the loop immediately
        
        # Calculate rate (requests per minute)
        elapsed = time.time() - start_time
        rpm_lms = (total_lms_api_calls / elapsed) * 60 if elapsed > 0 else 0
        rpm_gemini = (total_api_calls / elapsed) * 60 if elapsed > 0 else 0
        
        print(f"\n📊 Progress: {idx}/{len(all_submissions)} | ✅ {total_processed} completed | ❌ {total_failed} failed")
        print(f"⏱️  Time: {submission_time:.1f}s this submission | {elapsed/60:.1f}min total")
        print(f"📡 Rate: LMS={rpm_lms:.1f} req/min | Gemini={rpm_gemini:.1f} req/min")
        
        # Warnings if approaching limits
        if rpm_gemini > 12:
            print(f"⚠️  WARNING: Gemini rate approaching limit (15 req/min)")
        if rpm_lms > 50:
            print(f"⚠️  WARNING: LMS rate is high - risk of rate limiting")
        
        print("-" * 60)
        
        # Wait before next submission (rate limiting) - except for last one
        if idx < len(all_submissions):
            wait_between_requests()
    
    # Calculate final timing stats
    end_time = time.time()
    end_datetime = datetime.now()
    total_elapsed = end_time - start_time
    total_minutes = total_elapsed / 60
    total_hours = total_elapsed / 3600
    
    avg_time = sum(submission_times) / len(submission_times) if submission_times else 0
    min_time = min(submission_times) if submission_times else 0
    max_time = max(submission_times) if submission_times else 0
    
    # Calculate final rates
    final_rpm_lms = (total_lms_api_calls / total_elapsed) * 60 if total_elapsed > 0 else 0
    final_rpm_gemini = (total_api_calls / total_elapsed) * 60 if total_elapsed > 0 else 0
    
    # FINAL DETAILED SUMMARY
    print(f"\n{'='*70}")
    print(f"🎉 AUTOMATION COMPLETE!")
    print(f"{'='*70}")
    print(f"\n⏱️  TIMING SUMMARY:")
    print(f"   Started: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Ended: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Total Duration: {int(total_minutes)} min {int(total_elapsed % 60)} sec")
    if total_hours >= 1:
        print(f"   Total Duration: {total_hours:.2f} hours")
    print(f"   Avg per submission: {avg_time:.1f}s")
    print(f"   Fastest: {min_time:.1f}s | Slowest: {max_time:.1f}s")
    print(f"\n📊 OVERALL STATISTICS:")
    print(f"   Total Submissions Processed: {total_processed + total_failed}")
    print(f"   ✅ Successfully Handled: {total_processed}")
    print(f"   ❌ Failed to Process: {total_failed}")
    print(f"\n🌐 API USAGE & RATE LIMITS:")
    print(f"   📡 Gemini API Calls: {total_api_calls}")
    print(f"   📡 LMS API Calls: {total_lms_api_calls}")
    print(f"   📊 Avg Rate - Gemini: {final_rpm_gemini:.1f} req/min (limit: 15)")
    print(f"   📊 Avg Rate - LMS: {final_rpm_lms:.1f} req/min")
    print(f"   💰 Gemini Cost: $0.00 (Free tier)")
    print(f"   📊 Gemini Remaining today: ~{1500 - total_api_calls} requests (of 1,500 daily limit)")
    
    # Rate limit warnings
    if final_rpm_gemini > 10:
        print(f"\n   ⚠️  Gemini rate was {final_rpm_gemini:.1f} req/min - consider slower delays")
    else:
        print(f"\n   ✅ Gemini rate was safe ({final_rpm_gemini:.1f} req/min < 15 limit)")
    print(f"\n📝 BREAKDOWN BY TYPE:")
    print(f"   ✅ PDF Files (Graded): {total_pdf_graded}")
    print(f"   📄 DOC/DOCX Files (Rejected): {total_doc_files}")
    print(f"   📦 ZIP Files (Rejected): {total_zip_files}")
    print(f"   ⚠️  No Files Uploaded: {total_no_files}")
    print(f"   ❌ Other Invalid Formats: {total_invalid_format - total_doc_files - total_zip_files}")
    
    # Show failed attempts if any
    if failed_attempts:
        print(f"\n⚠️  FAILED SUBMISSIONS ({len(failed_attempts)}):")
        print(f"{'='*70}")
        for i, failed in enumerate(failed_attempts, 1):
            print(f"   {i}. {failed['student']} - {failed['assignment']}")
            print(f"      Reason: {failed['reason']}")
        
        print(f"\n💡 WHAT TO DO WITH FAILED SUBMISSIONS:")
        print(f"   1. Check the logs above for specific error messages")
        print(f"   2. Manually review these submissions in your LMS")
        print(f"   3. Common issues:")
        print(f"      • Network errors → Re-run the script")
        print(f"      • API timeout → Re-run the script")
        print(f"      • Corrupted files → Contact student for resubmission")
        print(f"   4. Files are saved in assignments/ folder for manual review")
    
    print(f"\n{'='*70}")
    print(f"📈 SUCCESS RATE: {(total_processed/(total_processed+total_failed)*100):.1f}%" if (total_processed+total_failed) > 0 else "N/A")
    print(f"{'='*70}")
    
    if total_invalid_format > 0:
        print(f"\n📌 NOTE: {total_invalid_format} students received 0 marks with")
        print(f"   instructions to resubmit in PDF format.")
        print(f"   They can resubmit and get automatically graded!")
    
    print(f"\n✅ All done! Check your LMS for submitted grades.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  Interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise
