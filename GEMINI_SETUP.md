# 🤖 Gemini AI Setup Guide

Quick guide to set up Google Gemini API for assignment review.

## Step 1: Install Required Library

```bash
pip install google-generativeai
```

## Step 2: Get Your FREE API Key

1. Visit: **https://makersuite.google.com/app/apikey**
2. Sign in with Google account
3. Click "Create API Key"
4. Copy the key (looks like: `AIzaSyC...`)

### Free Tier Limits:
- ✅ **60 requests per minute** (more than enough!)
- ✅ **Free forever** (no credit card needed)
- ✅ **Can read PDFs directly**
- ✅ **Perfect for assignment review**

## Step 3: Test It!

### Quick Test (without saving to .env):
```bash
python3 test_gemini.py YOUR_API_KEY_HERE
```

Example:
```bash
python3 test_gemini.py AIzaSyC_your_actual_key_here
```

### What the test does:
1. ✓ Checks if library is installed
2. ✓ Tests API connection
3. ✓ Tests basic text generation
4. ✓ Tests PDF review with a real file from `assignments/`

## Step 4: Add to .env (After Testing)

Once test works, add to your `.env` file:

```env
# AI Review Configuration
GEMINI_API_KEY=AIzaSyC_your_actual_key_here
```

## Step 5: Run with Main App

```bash
python3 auto_review.py
```

When you run it:
- It will show: `🤖 AI Review: ✅ Enabled (Gemini API)`
- You'll be asked: `Enable auto-submit marks & AI feedback?`
- Say **no** first time to just test reviews without submitting

## 🧪 Test Output Example

```
============================================================
🧪 Testing Gemini API for Assignment Review
============================================================

✓ Step 1: Checking if google-generativeai is installed...
  ✅ Library found!

✓ Step 2: Configuring Gemini API...
  ✅ API configured!

✓ Step 3: Testing basic text generation...
  ✅ Response: Hello, I'm working!

✓ Step 4: Testing PDF review...
  📄 Testing with: 4490152-Part1-Arrays-solution.pdf
  📤 Uploading file...
  ✅ Uploaded! URI: ...
  🤖 Generating AI review...

  ✅ AI Review Generated!

============================================================
AI RESPONSE:
============================================================
Assignment Type: Array Problems
Complete: Yes
Quality: 4/5 stars
Feedback: Good solutions with clear logic, but could add more comments.
============================================================

🎉 Gemini API Test Complete!
============================================================

✅ Your API key is working!
📝 You can now integrate this into auto_review.py
```

## ⚠️ Troubleshooting

### Error: "Library not found"
```bash
pip install google-generativeai
```

### Error: "API key invalid"
- Check you copied the full key
- Make sure there are no spaces
- Try generating a new key

### Error: "No PDF files found"
- Run `auto_review.py` first to download some assignments
- Or manually place a PDF in `assignments/` folder
- API is still working, just can't test PDF feature

### Error: "Quota exceeded"
- Free tier: 60 requests/min
- Wait 1 minute and try again
- You're probably not hitting this limit

## 💡 Tips

1. **Test first** with `test_gemini.py` before enabling in main app
2. **Start with no auto-submit** - review the AI suggestions manually first
3. **API is free** - no credit card, no charges ever
4. **Works offline** - downloads PDFs first, then reviews (no rate limit issues)

## 📊 Cost Comparison

| Option | Cost | Quality | Speed |
|--------|------|---------|-------|
| **Gemini (Free)** | $0 | ⭐⭐⭐⭐ | Fast |
| OpenAI GPT-4 | ~$0.03/review | ⭐⭐⭐⭐⭐ | Fast |
| Claude API | ~$0.015/review | ⭐⭐⭐⭐⭐ | Fast |
| Ollama (Local) | $0 | ⭐⭐⭐ | Slow |

**Recommendation:** Start with Gemini (free + good quality)!

