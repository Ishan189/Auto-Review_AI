"""
AI Reviewer - Reviews assignments using Google Gemini API
"""
import os
import google.generativeai as genai
from config import GEMINI_API_KEY


# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')  # Fast and efficient!
else:
    model = None


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


def review_assignment(filepath):
    """
    Review an assignment file using AI
    
    Returns: {
        'is_valid_format': bool,
        'can_review': bool,
        'review': str or None,
        'suggested_marks': int or None,
        'feedback': str
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
            'feedback': f"❌ Invalid file format ({ext}). Please submit as PDF."
        }
    
    # Check if AI can review this format
    if not can_ai_review:
        return {
            'is_valid_format': False,  # Treat as invalid to trigger 0 marks
            'can_review': False,
            'review': None,
            'suggested_marks': None,
            'feedback': f"❌ File format not supported for AI review ({ext}). Please convert to PDF and resubmit."
        }
    
    # Check if AI is configured
    if not model:
        return {
            'is_valid_format': True,
            'can_review': False,
            'review': None,
            'suggested_marks': None,
            'feedback': "⚠️ AI review not configured. Please set GEMINI_API_KEY in .env"
        }
    
    # Review with AI
    try:
        print(f"🤖 Reviewing {os.path.basename(filepath)} with AI...")
        
        # Gemini can only read PDF files directly via File API
        if ext == '.pdf':
            # Upload the file
            uploaded_file = genai.upload_file(filepath)
            
            prompt = """
You are an experienced programming instructor. Write BRIEF, encouraging feedback.

CRITICAL RULES:
- Maximum 800 characters for entire feedback (strictly enforce)
- Be concise but warm and human-like
- Never mention AI, automation, or being computer-generated
- Sound like a real teacher

Format EXACTLY like this:

=== REVIEW ===
Hi! [1 sentence about the submission]

**Strengths:**
- [2-3 brief positive points]

**Improvements Needed:**
- [2-3 brief, specific fixes]

[1 sentence encouragement]

=== SCORE ===
MARKS: [number only, 0-100]

JUSTIFICATION: [One brief sentence]

IMPORTANT: Keep the ENTIRE ==="REVIEW === section under 600 characters. Be concise!
"""
            
            response = model.generate_content([prompt, uploaded_file])
            review_text = response.text
            
            # Track API usage (this counts as 1 request to Gemini)
            print(f"  📡 API Call: 1 request to Gemini")
            
            # Enforce character limit
            MAX_CHARS = 800
            if len(review_text) > MAX_CHARS:
                print(f"  ⚠️  Feedback too long ({len(review_text)} chars), truncating to {MAX_CHARS}...")
                # Split by sections
                if '=== SCORE ===' in review_text:
                    review_part = review_text.split('=== SCORE ===')[0].strip()
                    score_part = '=== SCORE ===' + review_text.split('=== SCORE ===')[1]
                    
                    # Truncate review part if needed
                    max_review_chars = 600
                    if len(review_part) > max_review_chars:
                        review_part = review_part[:max_review_chars].rsplit('.', 1)[0] + '.'
                    
                    review_text = review_part + '\n\n' + score_part
                else:
                    # Fallback: simple truncation
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
                suggested_marks = min(max(marks, 0), 100)
            else:
                # Fallback: search for any number out of 100 pattern
                fallback_pattern = r'(\d+)\s*/\s*100'
                fallback_match = re.search(fallback_pattern, review_text)
                if fallback_match:
                    suggested_marks = int(fallback_match.group(1))
                else:
                    # Default if no marks found
                    suggested_marks = 70
                    print(f"  ⚠️ Could not parse marks, defaulting to {suggested_marks}")
            
            print(f"  📊 Extracted Score: {suggested_marks}/100")
            
            return {
                'is_valid_format': True,
                'can_review': True,
                'review': review_text,
                'suggested_marks': suggested_marks,
                'feedback': review_text
            }
    
    except Exception as e:
        print(f"❌ Error during AI review: {e}")
        return {
            'is_valid_format': True,
            'can_review': False,
            'review': None,
            'suggested_marks': None,
            'feedback': f"✅ File format valid, but AI review failed: {str(e)}"
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

