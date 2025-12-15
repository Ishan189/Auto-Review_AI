"""
AI Reviewer - Reviews assignments using Google Gemini API
"""
import os
from google import genai
from config import GEMINI_API_KEY, MODEL_NAME


# Configure Gemini with new API
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


def is_valid_file_type(filepath):
    """
    Check if file is supported by Gemini AI
    Returns: (is_valid: bool, extension: str, can_ai_review: bool)
    """
    # Only PDF is fully supported by Gemini File API
    ai_supported = ['.pdf']
    # DOC/DOCX are valid but need conversion
    valid_but_unsupported = ['.doc', '.docx']
    
    _, ext = os.path.splitext(filepath.lower())
    
    is_valid = ext in (ai_supported + valid_but_unsupported)
    can_ai_review = ext in ai_supported
    
    return is_valid, ext, can_ai_review


def review_assignment(filepath, max_retries=3, student_name=None, total_marks=100):
    """
    Review an assignment file using AI with retry logic
    
    Args:
        filepath: Path to the assignment file
        max_retries: Maximum number of retry attempts (default: 3)
        student_name: Optional student name to personalize feedback
        total_marks: Total marks for the assignment (default: 100)
    
    Returns: {
        'is_valid_format': bool,
        'can_review': bool,
        'review': str or None,
        'suggested_marks': int or None,
        'feedback': str,
        'retry_count': int
    }
    """
    # Check file type first
    is_valid, ext, can_ai_review = is_valid_file_type(filepath)
    
    if not is_valid:
        return {
            'is_valid_format': False,
            'can_review': False,
            'review': None,
            'suggested_marks': None,
            'feedback': f"❌ Invalid file format ({ext}). Please submit as PDF.",
            'retry_count': 0
        }
    
    # Check if AI can review this format
    if not can_ai_review:
        return {
            'is_valid_format': False,  # Treat as invalid to trigger 0 marks
            'can_review': False,
            'review': None,
            'suggested_marks': None,
            'feedback': f"❌ File format not supported for AI review ({ext}). Please convert to PDF and resubmit.",
            'retry_count': 0
        }
    
    # Check if AI is configured
    if not client:
        return {
            'is_valid_format': True,
            'can_review': False,
            'review': None,
            'suggested_marks': None,
            'feedback': "⚠️ AI review not configured. Please set GEMINI_API_KEY in .env",
            'retry_count': 0
        }
    
    # Review with AI - with retry logic
    import time
    retry_count = 0
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # Incremental backoff: 5s, 10s, 15s
                wait_time = 5 * attempt
                print(f"🔄 Retry attempt {attempt + 1}/{max_retries} (waiting {wait_time}s)...")
                time.sleep(wait_time)
            else:
                print(f"🤖 Reviewing {os.path.basename(filepath)} with AI...")
            
            retry_count = attempt + 1
            
            # Gemini can only read PDF files directly via File API
            if ext == '.pdf':
                # Upload PDF file using new API
                print(f"  📤 Uploading PDF file...")
                uploaded_file = client.files.upload(file=filepath)
                print(f"  ✅ File uploaded successfully")
            
            # Get first name from student_name if provided
            first_name = ""
            if student_name:
                first_name = student_name.split()[0]  # Get first name
            
            prompt = f"""
You are a programming instructor reviewing this student's assignment. Give helpful feedback.

STRICT RULES:
- MAXIMUM 800 characters total (CRITICAL - will be truncated if longer)
- Be warm, sound like a real teacher (never mention AI)
- Give specific feedback with examples
- Balance praise with constructive criticism

FORMAT:

=== REVIEW ===
Hi{' ' + first_name if first_name else ''}! [1 sentence about submission]

**Strengths:**
- [2-3 brief specific points about what worked well]

**Areas for Improvement:**
- [2-3 brief points: what's wrong, how to fix]

**Moving Forward:**
- [1 tip for improvement]


=== SCORE ===
MARKS: [number 0-{total_marks}]

KEEP IT BRIEF! Reference specific problems from the PDF. Max 800 characters!
"""
            
            # Generate review using new API
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, uploaded_file]
            )
            review_text = response.text
            
            # Track API usage (this counts as 1 request to Gemini)
            print(f"  📡 API Call: 1 request to Gemini")
            
            # Check and enforce strict character limit of 800
            word_count = len(review_text.split())
            print(f"  📝 Feedback length: {len(review_text)} chars, ~{word_count} words")
            
            # STRICT 800 character limit
            MAX_CHARS = 800
            if len(review_text) > MAX_CHARS:
                print(f"  ⚠️  Feedback too long ({len(review_text)} chars), truncating to {MAX_CHARS}...")
                # Split by sections to preserve structure
                if '=== SCORE ===' in review_text:
                    review_part = review_text.split('=== SCORE ===')[0].strip()
                    score_part = '=== SCORE ===' + review_text.split('=== SCORE ===')[1]
                    
                    # Truncate review part to fit within limit (reserve ~150 chars for score section)
                    max_review_chars = 600
                    if len(review_part) > max_review_chars:
                        review_part = review_part[:max_review_chars].rsplit('.', 1)[0] + '.'
                    
                    review_text = review_part + '\n\n' + score_part
                    
                    # Final check - if still too long, hard truncate
                    if len(review_text) > MAX_CHARS:
                        review_text = review_text[:MAX_CHARS].rsplit('.', 1)[0] + '.'
                else:
                    # Fallback: simple truncation at sentence boundary
                    review_text = review_text[:MAX_CHARS].rsplit('.', 1)[0] + '.'
                
                print(f"  ✅ Truncated to {len(review_text)} characters")
            
            # Parse marks from response (improved parsing)
            import re
            suggested_marks = None
            
            # Try to find MARKS: line
            marks_pattern = r'MARKS:\s*(\d+)'
            match = re.search(marks_pattern, review_text, re.IGNORECASE)
            
            if match:
                marks = int(match.group(1))
                # Ensure it's within valid range
                suggested_marks = min(max(marks, 0), total_marks)
            else:
                # Fallback: search for any number out of total_marks pattern
                fallback_pattern = rf'(\d+)\s*/\s*{total_marks}'
                fallback_match = re.search(fallback_pattern, review_text)
                if fallback_match:
                    suggested_marks = int(fallback_match.group(1))
                else:
                    # Default if no marks found (70% of total)
                    suggested_marks = int(total_marks * 0.7)
                    print(f"  ⚠️ Could not parse marks, defaulting to {suggested_marks}")
            
            print(f"  📊 Extracted Score: {suggested_marks}/{total_marks}")
            
            return {
                'is_valid_format': True,
                'can_review': True,
                'review': review_text,
                'suggested_marks': suggested_marks,
                'feedback': review_text,
                'retry_count': retry_count
            }
        
        except Exception as e:
            last_error = e
            print(f"❌ Error during AI review (attempt {attempt + 1}/{max_retries}): {e}")
            
            # If this is not the last attempt, continue to retry
            if attempt < max_retries - 1:
                continue
            else:
                # All retries exhausted
                print(f"❌ All {max_retries} retry attempts failed!")
                return {
                    'is_valid_format': False,
                    'can_review': False,
                    'review': None,
                    'suggested_marks': None,
                    'feedback': f"AI_REVIEW_FAILED: {str(last_error)}",
                    'retry_count': retry_count,
                    'error': str(last_error)
                }
    
    # This shouldn't be reached, but just in case
    return {
        'is_valid_format': False,
        'can_review': False,
        'review': None,
        'suggested_marks': None,
        'feedback': f"AI_REVIEW_FAILED: {str(last_error) if last_error else 'Unknown error'}",
        'retry_count': retry_count,
        'error': str(last_error) if last_error else 'Unknown error'
    }


def format_feedback_for_submission(review_result):
    """
    Format the review result into HTML for submission - looks like human feedback
    """
    if not review_result['is_valid_format']:
        # Invalid format - clear message
        return f"<p>{review_result['feedback']}</p>"
    
    if not review_result['can_review']:
        # Valid format but couldn't review
        return f"<p>{review_result['feedback']}</p>"
    
    # Format feedback to look natural
    import re
    feedback = review_result['feedback']
    
    # Remove the === REVIEW === header and === SCORE === section
    if '=== SCORE ===' in feedback:
        feedback = feedback.split('=== SCORE ===')[0].strip()
    if '=== REVIEW ===' in feedback:
        feedback = feedback.split('=== REVIEW ===')[1].strip()
    
    # Convert markdown-style bold to HTML
    feedback = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', feedback)
    
    # Convert bullet points
    feedback = feedback.replace('\n- ', '\n• ')
    
    # Convert line breaks to HTML
    feedback = feedback.replace('\n\n', '<br><br>')
    feedback = feedback.replace('\n', '<br>')
    
    return f"""<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; color: #333; padding: 15px;">
{feedback}
</div>"""

