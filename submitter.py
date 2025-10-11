"""
Submission Handler - Submits marks and feedback to API
"""
import json
import requests
from config import BASE_URL, HEADERS


def submit_marks_and_feedback(submission_details, marks, feedback_html):
    """
    Submit marks and feedback for a submission
    
    Args:
        submission_details: Full submission details from API
        marks: Integer 0-100
        feedback_html: HTML formatted feedback
        
    Returns:
        success: bool, response: dict
    """
    exercise = submission_details["exercise"]
    
    attempt_id = exercise["attempt_id"]
    exercise_id = exercise["exercise_id"]
    exercise_name = exercise["exercise_name"]
    class_id = exercise["class_id"]
    
    url = f"{BASE_URL}/assignment/attempt/{attempt_id}/marks"
    
    payload = {
        "exercise_id": exercise_id,
        "exercise_name": exercise_name,
        "test_parts": "[]",
        "class_id": class_id,
        "user_test_time": 0,
        "mark": str(marks),
        "faculty_comments": feedback_html
    }
    
    try:
        files = {"JSONString": (None, json.dumps(payload))}
        response = requests.post(url, headers=HEADERS, files=files, timeout=30)
        response.raise_for_status()
        
        print(f"\n   ✅ SUBMITTED TO LMS SUCCESSFULLY!")
        return True, response.json()
        
    except Exception as e:
        print(f"\n   ❌ SUBMISSION FAILED: {e}")
        return False, None

