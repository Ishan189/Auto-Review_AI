# Configuration Guide

## Setup Your `.env` File

Add these variables to your `.env` file to configure the script:

```env
# API Configuration (Required)
API_KEY=your_api_key_here
ORG_ID=your_org_id_here
BASE_URL=https://tutort-api.edmingle.com/nuSource/api/v1

# Rate Limiting Configuration (Optional - defaults shown)
MIN_DELAY_BETWEEN_REQUESTS=2     # Wait 2-5 seconds between submissions
MAX_DELAY_BETWEEN_REQUESTS=5
MIN_DELAY_BETWEEN_BATCHES=5      # Wait 5-10 seconds between batches
MAX_DELAY_BETWEEN_BATCHES=10
BATCH_SIZE=10                     # Process 10 submissions per batch
RETRY_BASE_DELAY=10              # Wait 15-25s on first retry, 35-45s on second, etc.
MAX_RETRIES=3                    # Try 3 times before giving up
```

## Rate Limiting Prevention Strategy

### Current Configuration (Safe & Recommended)
- **Between requests**: 2-5 seconds random delay
- **Between batches**: 5-10 seconds random delay
- **Batch size**: 10 submissions
- **Retry strategy**: Exponential backoff (15s → 35s → 65s)

### If You Get Rate Limited Often
Increase the delays:
```env
MIN_DELAY_BETWEEN_REQUESTS=5     # Slower
MAX_DELAY_BETWEEN_REQUESTS=10
MIN_DELAY_BETWEEN_BATCHES=15     # Much slower between batches
MAX_DELAY_BETWEEN_BATCHES=30
BATCH_SIZE=5                     # Smaller batches
```

### If You Want Faster Processing (Risky!)
Decrease the delays (not recommended):
```env
MIN_DELAY_BETWEEN_REQUESTS=1     # Faster but risky
MAX_DELAY_BETWEEN_REQUESTS=3
MIN_DELAY_BETWEEN_BATCHES=3
MAX_DELAY_BETWEEN_BATCHES=5
```

### For Overnight Processing
Use very conservative settings:
```env
MIN_DELAY_BETWEEN_REQUESTS=10    # Super safe
MAX_DELAY_BETWEEN_REQUESTS=20
MIN_DELAY_BETWEEN_BATCHES=30
MAX_DELAY_BETWEEN_BATCHES=60
BATCH_SIZE=5
```

## How It Works

1. **Random Delays**: Uses random values between min/max to look human
2. **Exponential Backoff**: If rate-limited, waits increasingly longer
3. **Batch Processing**: Processes 10 submissions, then asks to continue
4. **Smart Retry**: Automatically retries with longer waits if blocked

## Tips to Avoid Rate Limiting

✅ **Do:**
- Keep default settings for first run
- Process during off-peak hours (late night/early morning)
- Let the script handle retries automatically
- Process in batches with breaks

❌ **Don't:**
- Set delays below 1 second
- Process more than 10 submissions per batch
- Skip the delays between batches
- Run multiple instances simultaneously

## Monitoring

The script will show:
- `⏳ Waiting X.Xs before next submission...` - Normal delay
- `⚠️ Rate limited! Waiting Xs before retry...` - Got blocked, retrying
- `❌ You are currently rate-limited!` - Need to wait 15-30 minutes

## Support

If you consistently get rate limited even with safe settings:
1. Wait 30 minutes before trying again
2. Increase all delay values by 2x
3. Reduce BATCH_SIZE to 5
4. Contact API provider for higher rate limits

