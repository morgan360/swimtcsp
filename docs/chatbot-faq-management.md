# Chatbot FAQ Management Guide

This guide explains how to manage FAQs for the TCSP chatbot system, including adding new FAQs, embedding them, and troubleshooting.

## Overview

The chatbot answers in **three tiers**. One embedding of the user's question
decides which:

| Tier | Condition | Behaviour | API cost |
|------|-----------|-----------|----------|
| Match | score ≥ `FAQ_MATCH_THRESHOLD` | Stored answer, verbatim | embedding only |
| Hedged | score ≥ `FAQ_MIN_CONFIDENCE` | Stored answer, prefixed "I'm not certain, but this may help" | embedding only |
| Miss | below that | Model call, **with** any FAQ scoring above `FAQ_CONTEXT_MIN_SCORE` injected as grounding | embedding + completion |

A question that exactly matches a stored one (ignoring case and spacing) is
answered with **no API call at all**. Query embeddings are cached for 24h, so
repeats are free after the first.

The model tier still receives live data — swim sessions, term dates, lesson
lists — as it always did.

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
OPENAI_API_KEY=sk-proj-...                  # Your OpenAI API key
OPENAI_EMBED_MODEL=text-embedding-3-small   # Embedding model
OPENAI_CHAT_MODEL=gpt-5.4-mini              # Chat completion model
FAQ_MATCH_THRESHOLD=0.65                    # Serve the stored answer at or above this
FAQ_MIN_CONFIDENCE=0.45                     # Serve it hedged at or above this
FAQ_CONTEXT_MIN_SCORE=0.40                  # Inject as prompt grounding at or above this
CHATBOT_MAX_MESSAGES_PER_HOUR=30            # Per-session throttle (0 disables)
CHATBOT_MAX_MESSAGE_CHARS=500               # Message length cap
```

All of these are declared **once**, in `config/base_settings.py`. The
per-environment settings files no longer override them — they used to, with
different defaults each, which meant the model actually in use depended on
whether the process environment happened to carry the variable.

**Important:** the embedding model must be the same one that built
`FAQEntry.embedding`. Changing `OPENAI_EMBED_MODEL` requires
`python manage.py rebuild_faq_embeddings --force`; otherwise queries are scored
against vectors from a different space, which degrades matching without ever
raising an error.

**Model parameters:** `chatbot/helpers/client.py` shapes the call per model —
gpt-5.x rejects `max_tokens` and non-default `temperature`, so those go only to
the models in `LEGACY_PARAM_MODELS`.

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

2. Sync and embed:
   ```bash
   python manage.py rebuild_faq_embeddings
   ```

## Management Commands & Scripts

### Quick Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `python manage.py embed_new_faqs` | Embed FAQs without embeddings | After adding FAQ in admin |
| `python manage.py import_faqs` | Import FAQs from YAML | Initial setup or bulk import |

### Full Re-sync

Use this when changing embedding models, after editing `faq.yaml`, or during
cleanup:

```bash
python manage.py rebuild_faq_embeddings --force
```

Reads `chatbot/data/faq.yaml`, upserts every entry, and re-embeds using the
configured model. Add `--delete-orphans` to remove database entries no longer
present in the YAML.

To go the other way (database → YAML):

```bash
python export_faqs.py
```

> The old `embed_faqs.py` / `update_faq_embeddings.py` chain has been retired.
> It embedded the question alone and pinned both the settings module and the
> model, so it would now write vectors the matcher cannot use.

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
# 2. Re-embed everything with the new model
python manage.py rebuild_faq_embeddings --force
```

No restart needed — saving a FAQ invalidates the in-memory vector index.

### Syncing Production Database to Local

```bash
# 1. On production: export FAQs to YAML
python export_faqs.py

# 2. Copy chatbot/data/faq.yaml to your local checkout
# 3. Locally: import and embed
python manage.py rebuild_faq_embeddings --force
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
# Confirm every environment agrees on the model
python manage.py shell -c "from chatbot.helpers.client import embed_model; print(embed_model())"

# Re-embed all FAQs with it
python manage.py rebuild_faq_embeddings --force
```

### Issue: OpenAI API 401 Unauthorized

**Cause:** Invalid or expired API key

**Fix:**
1. Get new API key from https://platform.openai.com/api-keys
2. Update `.env`: `OPENAI_API_KEY=sk-proj-...`
3. Restart Django server

### Issue: FAQs in Database but Not in YAML

**Symptoms:**
- The database holds more FAQs than `faq.yaml` lists
- `rebuild_faq_embeddings` reports fewer entries than you expect

**Fix:**
```bash
# Export all FAQs from database to YAML
python export_faqs.py

# Then re-import and embed from it
python manage.py rebuild_faq_embeddings --force
```

## File Structure

```
swimtcsp/
├── chatbot/
│   ├── data/
│   │   └── faq.yaml                      # Source of truth for FAQ content
│   ├── management/
│   │   └── commands/
│   │       ├── rebuild_faq_embeddings.py # YAML → DB + embeddings (deploy path)
│   │       ├── embed_new_faqs.py         # Embed DB rows missing a vector
│   │       ├── import_faqs.py            # Import from YAML, no embeddings
│   │       └── faq_calibrate.py          # Threshold calibration report
│   ├── helpers/
│   │   ├── client.py                     # Model choice + safe OpenAI calls
│   │   ├── faq.py                        # Three-tier matching
│   │   ├── faq_index.py                  # Cached vector index
│   │   ├── throttle.py                   # Per-session rate limit
│   │   ├── gpt.py                        # Prompt builders + HTML sanitising
│   │   ├── swim.py                       # Swim session helpers
│   │   └── lesson.py                     # Lesson helpers
│   ├── signals.py                        # Invalidate index on FAQ save
│   ├── models.py                         # FAQEntry, ChatbotQuery
│   ├── views.py                          # Chatbot API endpoints
│   └── urls.py                           # Chatbot routes
├── static/chatbot/chat.js                # Shared chat widget (both bots)
├── export_faqs.py                        # Export DB → YAML
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
- **False** - General questions (hours, payment, lockers, hats). Visible to **both** bots.
- **True** - Lesson-specific (skill progression, assessments, term dates). Visible to the **lesson bot only**.

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

### Abuse protection
Both chatbot endpoints are public, and every message can spend credits. Each
session is capped at `CHATBOT_MAX_MESSAGES_PER_HOUR` messages and each message
at `CHATBOT_MAX_MESSAGE_CHARS` characters. Set the hourly cap to `0` to disable
throttling entirely (not recommended in production).

## Monitoring & Analytics

### Calibration report (start here)

```bash
python manage.py faq_calibrate --days 90
```

Prints the tier mix, the confidence-score distribution, the near-miss band and
the most frequently asked questions. Set the three thresholds from this rather
than guessing, and turn recurring near-misses into new FAQ entries.

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

2. **Deploy the code** (`faq.yaml` travels with it).

3. **Rebuild embeddings** — `deploy-to-production.sh` does this for you and now
   aborts the deploy if it fails. Manually:
   ```bash
   cd ~/swimtcsp
   python manage.py rebuild_faq_embeddings
   ```

4. **Reload web app** via PythonAnywhere dashboard

### Continuous Updates

For production FAQ updates, either:

**Via admin (fastest)** — add the FAQ in `/generaladmin/`, select it, and run
the "Generate embeddings using OpenAI" action. It takes effect immediately; no
reload needed.

**Via YAML (version-controlled, preferred)**:
1. Edit `chatbot/data/faq.yaml`
2. `python manage.py rebuild_faq_embeddings` locally to test
3. Commit and deploy — the deploy script rebuilds embeddings on production

## API Costs

Approximate OpenAI costs (as of 2025):

Check current pricing at https://platform.openai.com/docs/pricing — the figures
that used to be quoted here went stale.

What actually drives the bill:

- A **Match** or **Hedged** answer costs one embedding call, and nothing if the
  question was asked before (24h query-embedding cache) or matches a stored
  question exactly.
- A **Miss** costs an embedding *and* a completion. Completions are capped at
  600 tokens.
- FAQ embeddings are a one-off per entry, regenerated only on
  `rebuild_faq_embeddings`.

**Takeaway:** maximise Match/Hedged answers. Run `manage.py faq_calibrate` to
see the current tier mix and which questions keep falling through.

## Related Documentation

- [Chatbot App Overview](../CLAUDE.md#chatbot) - Architecture and integration
- [OpenAI Embeddings Docs](https://platform.openai.com/docs/guides/embeddings) - API reference
- [Django Management Commands](https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/) - Creating custom commands

## Support

For issues or questions:
1. Check logs: `tail -f logs/application.log`
2. Run `python manage.py faq_calibrate` for confidence scores
3. Test with a question copied verbatim from a FAQ (should answer from the FAQ tier)
4. Verify the API key and model resolve:
   ```bash
   python manage.py shell -c "from chatbot.helpers.client import chat_model, embed_model, get_client; print(chat_model(), embed_model()); get_client().models.list()"
   ```

---

**Last Updated:** 2026-08-07
**Embedding Model:** text-embedding-3-small
**Chat Model:** gpt-5.4-mini