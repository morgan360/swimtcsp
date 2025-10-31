# Chatbot FAQ Management Guide

This guide explains how to manage FAQs for the TCSP chatbot system, including adding new FAQs, embedding them, and troubleshooting.

## Overview

The chatbot uses a **hybrid approach** combining pre-stored FAQs with OpenAI GPT responses:

1. **FAQ Matching** - Uses OpenAI embeddings + cosine similarity to match user questions to stored FAQs
2. **GPT Fallback** - If no FAQ matches (confidence < threshold), falls back to GPT with real-time data

## Key Components

### Models (`chatbot/models.py`)

- **FAQEntry** - Stores FAQ questions, answers, and embeddings
  - `question` - The FAQ question text
  - `answer` - The answer (supports rich text via CKEditor)
  - `embedding` - JSON field storing the OpenAI embedding vector (1536 dimensions)
  - `lessons_only` - Boolean flag (True = lesson chatbot only, False = available to both)

- **ChatbotQuery** - Logs all chatbot interactions for analytics
  - Tracks user, message, response_type (FAQ/GPT), confidence score, timestamp

### Configuration

Key settings in `.env`:

```bash
OPENAI_API_KEY=sk-proj-...           # Your OpenAI API key
OPENAI_EMBED_MODEL=text-embedding-3-small  # Embedding model
OPENAI_CHAT_MODEL=gpt-4o-mini        # Chat completion model
FAQ_MATCH_THRESHOLD=0.65             # Minimum cosine similarity score (0.0-1.0)
```

**Important:** The embedding model must match between:
- FAQ generation (`embed_faqs.py`)
- Query matching (`chatbot/views.py`)

## Adding New FAQs

### Method 1: Via Django Admin (Recommended)

1. Log into Django admin: `/admin/`
2. Navigate to **Chatbot → FAQ Entries**
3. Click **Add FAQ Entry**
4. Fill in:
   - Question
   - Answer (supports HTML formatting)
   - Lessons only (check if lesson-specific)
5. Save
6. Run embedding command:
   ```bash
   python manage.py embed_new_faqs
   ```

### Method 2: Via YAML File

1. Edit `chatbot/data/faq.yaml`:
   ```yaml
   - question: What are your opening hours?
     answer: We are open Monday-Friday 9am-9pm, weekends 10am-6pm.
     lessons_only: false  # Optional, defaults to false
   ```

2. Run embedding script:
   ```bash
   python embed_faqs.py
   ```

3. Update database:
   ```bash
   python update_faq_embeddings.py
   ```

## Management Commands & Scripts

### Quick Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `python manage.py embed_new_faqs` | Embed FAQs without embeddings | After adding FAQ in admin |
| `python manage.py import_faqs` | Import FAQs from YAML | Initial setup or bulk import |

### Full Re-sync Scripts

Use these when changing embedding models or doing major cleanup:

#### 1. Export FAQs from Database
```bash
python export_faqs.py
```
- Exports all FAQs from database to `chatbot/data/faq.yaml`
- Creates backup of existing YAML file
- Includes `lessons_only` flags

#### 2. Embed All FAQs
```bash
# From YAML file (default)
python embed_faqs.py

# Or directly from database
python embed_faqs.py --from-db
```
- Generates OpenAI embeddings for all questions
- Saves to `chatbot/data/faq_with_embeddings.json`
- Takes ~1 second per FAQ (rate limiting)

#### 3. Update Database
```bash
python update_faq_embeddings.py
```
- Syncs embeddings from JSON file to database
- Matches by question text
- Updates `lessons_only` flags if present

## Common Workflows

### Adding a Single FAQ

```bash
# 1. Add FAQ via Django admin
# 2. Run embedding command
python manage.py embed_new_faqs
# 3. Done! (No server restart needed)
```

### Bulk Update (Changing Embedding Model)

```bash
# 1. Update OPENAI_EMBED_MODEL in .env
# 2. Export current FAQs
python export_faqs.py

# 3. Re-embed all with new model
python embed_faqs.py

# 4. Update database
python update_faq_embeddings.py

# 5. Restart Django server
python manage.py runserver
```

### Syncing Production Database to Local

```bash
# 1. Export FAQs from production database
python export_faqs.py

# 2. Copy faq.yaml to local environment
# 3. Embed locally (uses local API key)
python embed_faqs.py

# 4. Update local database
python update_faq_embeddings.py
```

## Troubleshooting

### Issue: FAQ Not Matching User Question

**Symptoms:**
- Chatbot logs show low confidence score (< 0.65)
- Response type is "GPT" instead of "FAQ"

**Diagnosis:**
```bash
python manage.py shell
```
```python
from chatbot.models import ChatbotQuery

# Check recent queries
recent = ChatbotQuery.objects.order_by('-timestamp')[:10]
for q in recent:
    print(f"{q.message[:50]} | {q.response_type} | {q.confidence_score}")
```

**Solutions:**
1. **Lower threshold** - Edit `.env`: `FAQ_MATCH_THRESHOLD=0.60`
2. **Add similar variations** - Create additional FAQ entries with alternate phrasings
3. **Check embeddings exist** - Run `python manage.py embed_new_faqs`

### Issue: Identical Question Has Low Score

**Cause:** Embedding model mismatch or old embeddings

**Fix:**
```bash
# Check embedding model in views.py matches embed_faqs.py
grep "EMBED_MODEL" .env
grep "model=" embed_faqs.py

# Re-embed all FAQs
python export_faqs.py
python embed_faqs.py
python update_faq_embeddings.py
```

### Issue: OpenAI API 401 Unauthorized

**Cause:** Invalid or expired API key

**Fix:**
1. Get new API key from https://platform.openai.com/api-keys
2. Update `.env`: `OPENAI_API_KEY=sk-proj-...`
3. Restart Django server

### Issue: FAQs in Database but Not in YAML

**Symptoms:**
- Database has 72 FAQs
- YAML only has 21 FAQs
- `embed_faqs.py` only processes 21

**Fix:**
```bash
# Export all FAQs from database to YAML
python export_faqs.py

# Now YAML will have all 72 FAQs
python embed_faqs.py
python update_faq_embeddings.py
```

## File Structure

```
swimtcsp/
├── chatbot/
│   ├── data/
│   │   ├── faq.yaml                      # Source FAQ questions/answers
│   │   └── faq_with_embeddings.json      # Generated embeddings
│   ├── management/
│   │   └── commands/
│   │       ├── import_faqs.py            # Import from YAML to DB
│   │       └── embed_new_faqs.py         # Embed new FAQs only
│   ├── helpers/
│   │   ├── faq.py                        # FAQ matching logic
│   │   ├── gpt.py                        # GPT prompt builders
│   │   ├── swim.py                       # Swim session helpers
│   │   └── lesson.py                     # Lesson helpers
│   ├── models.py                         # FAQEntry, ChatbotQuery
│   ├── views.py                          # Chatbot API endpoints
│   └── urls.py                           # Chatbot routes
├── embed_faqs.py                         # Standalone embedding script
├── export_faqs.py                        # Export DB → YAML
├── update_faq_embeddings.py              # Sync JSON → DB
└── docs/
    └── chatbot-faq-management.md         # This file
```

## Best Practices

### 1. Use Semantic Questions
Write questions the way users would ask them:
- ✅ "Do I need to wear a swimming hat?"
- ❌ "Swimming hat requirement policy"

### 2. Test New FAQs
After adding a FAQ, test it in the chatbot UI:
```
User: [Type your question exactly as written in FAQ]
Bot: [Should return the FAQ answer, not GPT]
```

Check the `ChatbotQuery` table to see confidence scores.

### 3. Monitor Confidence Scores
Review chatbot logs regularly:
```python
# Check common questions with low confidence
from chatbot.models import ChatbotQuery

low_confidence = ChatbotQuery.objects.filter(
    response_type='GPT',
    confidence_score__isnull=False,
    confidence_score__gt=0.50,
    confidence_score__lt=0.65
).order_by('-timestamp')[:20]

for q in low_confidence:
    print(f"{q.confidence_score:.2f} | {q.message}")
```

These are questions that *almost* matched an FAQ. Consider:
- Adding them as new FAQs
- Lowering the threshold
- Updating existing FAQ wording

### 4. Separate Swim vs Lesson FAQs
Use the `lessons_only` flag appropriately:
- **False** - General questions (hours, payment, lockers, hats)
- **True** - Lesson-specific (skill progression, assessments, term dates)

### 5. Keep Answers Concise
- Use bullet points for lists
- Bold important information
- Include links where relevant
- Avoid very long paragraphs (GPT can handle those better)

## Performance Optimization

### Reduce Embedding Costs
- Only embed new FAQs: `python manage.py embed_new_faqs`
- Use `text-embedding-3-small` (cheaper than ada-002)
- Cache frequently asked questions

### Improve Match Rates
- Lower threshold for more FAQ hits: `FAQ_MATCH_THRESHOLD=0.60`
- Add question variations as separate FAQ entries
- Review `ChatbotQuery` logs monthly for missed questions

### API Rate Limits
The `embed_faqs.py` script includes a 1-second delay per FAQ to avoid rate limits:
```python
time.sleep(1)  # In get_embedding() function
```

For faster processing, adjust based on your OpenAI tier limits.

## Monitoring & Analytics

### Check FAQ Hit Rate
```python
from chatbot.models import ChatbotQuery
from django.db.models import Count

# Last 30 days
from datetime import timedelta
from django.utils import timezone

thirty_days_ago = timezone.now() - timedelta(days=30)

stats = ChatbotQuery.objects.filter(
    timestamp__gte=thirty_days_ago
).values('response_type').annotate(count=Count('id'))

for stat in stats:
    print(f"{stat['response_type']}: {stat['count']}")
```

### Most Common Questions
```python
from chatbot.models import ChatbotQuery
from django.db.models import Count

top_questions = ChatbotQuery.objects.values('message').annotate(
    count=Count('id')
).order_by('-count')[:20]

for q in top_questions:
    print(f"{q['count']:3d} | {q['message'][:60]}")
```

## Production Deployment

### PythonAnywhere Setup

1. **Set environment variables** in PythonAnywhere web app settings:
   - `OPENAI_API_KEY`
   - `OPENAI_EMBED_MODEL`
   - `FAQ_MATCH_THRESHOLD`

2. **Upload FAQ data**:
   ```bash
   # On local machine
   scp chatbot/data/faq_with_embeddings.json username@ssh.pythonanywhere.com:~/swimtcsp/chatbot/data/
   ```

3. **Update database**:
   ```bash
   # On PythonAnywhere console
   cd ~/swimtcsp
   python manage.py shell < update_faq_embeddings.py
   ```

4. **Reload web app** via PythonAnywhere dashboard

### Continuous Updates

For production FAQ updates:
1. Add FAQ locally via Django admin
2. Run `python manage.py embed_new_faqs` locally
3. Export updated FAQ: `python export_faqs.py`
4. Deploy YAML and JSON files to production
5. Run `python update_faq_embeddings.py` on production
6. Reload production web app

## API Costs

Approximate OpenAI costs (as of 2025):

| Model | Cost | Use Case |
|-------|------|----------|
| `text-embedding-3-small` | $0.020 / 1M tokens | FAQ embeddings |
| `gpt-4o-mini` | $0.150 / 1M input tokens | Chat responses |

### Cost Example (72 FAQs):
- Embedding 72 questions (~1000 tokens total) = $0.00002
- 1000 FAQ matches = $0 (no API call)
- 1000 GPT responses = ~$0.15

**Takeaway:** Maximize FAQ matches to minimize costs!

## Related Documentation

- [Chatbot App Overview](../CLAUDE.md#chatbot) - Architecture and integration
- [OpenAI Embeddings Docs](https://platform.openai.com/docs/guides/embeddings) - API reference
- [Django Management Commands](https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/) - Creating custom commands

## Support

For issues or questions:
1. Check Django logs: `tail -f logs/django.log`
2. Review ChatbotQuery table for confidence scores
3. Test embeddings with identical questions (should score >0.95)
4. Verify API key is valid: `python -c "import openai; client = openai.OpenAI(); print(client.models.list())"`

---

**Last Updated:** 2025-10-31
**Embedding Model:** text-embedding-3-small
**Chat Model:** gpt-4o-mini