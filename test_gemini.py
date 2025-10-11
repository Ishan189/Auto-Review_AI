"""
Simple test script for Gemini API
Tests PDF review functionality before integrating into main app
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from command line or environment
if len(sys.argv) > 1:
    GEMINI_API_KEY = sys.argv[1]
else:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ No API key provided!")
    print("\nUsage:")
    print("  python3 test_gemini.py YOUR_API_KEY")
    print("  OR set GEMINI_API_KEY in .env file")
    print("\n🔑 Get your free API key:")
    print("  https://makersuite.google.com/app/apikey")
    sys.exit(1)

print("=" * 60)
print("🧪 Testing Gemini API for Assignment Review")
print("=" * 60)

# Test 1: Check if library is installed
print("\n✓ Step 1: Checking if google-generativeai is installed...")
try:
    import google.generativeai as genai
    print("  ✅ Library found!")
except ImportError:
    print("  ❌ Library not found!")
    print("\n  Install it with:")
    print("    pip install google-generativeai")
    sys.exit(1)

# Test 2: Configure API
print("\n✓ Step 2: Configuring Gemini API...")
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("  ✅ API configured!")
except Exception as e:
    print(f"  ❌ Configuration failed: {e}")
    sys.exit(1)

# Test 3: Simple text test
print("\n✓ Step 3: Testing basic text generation...")
try:
    response = model.generate_content("Say 'Hello, I'm working!' in 5 words or less")
    print(f"  ✅ Response: {response.text.strip()}")
except Exception as e:
    print(f"  ❌ Text test failed: {e}")
    sys.exit(1)

# Test 4: PDF review test
print("\n✓ Step 4: Testing PDF review...")

# Find a PDF in assignments folder
pdf_files = []
assignments_dir = "assignments"
if os.path.exists(assignments_dir):
    for file in os.listdir(assignments_dir):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(assignments_dir, file))

if not pdf_files:
    print("  ⚠️  No PDF files found in assignments/ folder")
    print("  Skipping PDF test - but API is working!")
else:
    test_pdf = pdf_files[0]
    print(f"  📄 Testing with: {os.path.basename(test_pdf)}")
    
    try:
        # Upload the PDF
        print("  📤 Uploading file...")
        uploaded_file = genai.upload_file(test_pdf)
        print(f"  ✅ Uploaded! URI: {uploaded_file.uri}")
        
        # Generate review
        print("  🤖 Generating AI review...")
        prompt = """
This is a programming assignment submission. Please provide a brief review (Strict CHECK: Maximum 1000 characters)
1. What type of assignment is this? (2-3 words)
2. Is it complete? (Yes/No/Partial)
3. Rate the quality (1-5 stars)
4. One sentence of feedback

Keep your response SHORT (under 50 words).
"""
        
        response = model.generate_content([prompt, uploaded_file])
        print(f"\n  ✅ AI Review Generated!")
        print("\n" + "=" * 60)
        print("AI RESPONSE:")
        print("=" * 60)
        print(response.text)
        print("=" * 60)
        
    except Exception as e:
        print(f"  ❌ PDF test failed: {e}")
        print(f"\n  Error details: {type(e).__name__}")
        if hasattr(e, 'response'):
            print(f"  Response: {e.response}")

print("\n" + "=" * 60)
print("🎉 Gemini API Test Complete!")
print("=" * 60)
print("\n✅ Your API key is working!")
print("📝 You can now integrate this into auto_review.py")
print("\n💡 To use in main app:")
print("  1. Add to .env: GEMINI_API_KEY=your_key_here")
print("  2. Run: python3 auto_review.py")

