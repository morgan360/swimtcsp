# FAQ Content Review — items needing your decision

Companion to the 2026-08-07 chatbot overhaul. Everything below was found while
auditing `chatbot/data/faq.yaml`. **No edits were made to any of it** — these
are policy and pricing calls that need the pool's sign-off, not a developer's
judgement.

Mechanical fixes (typos, a stale URL, duplicate merges, `lessons_only` tagging)
*were* applied — see the commit. The corpus went from 72 entries to 69.

---

## 1. Contradictions — the bot currently gives different answers to the same question

### Under-8 / under-12 supervision — three different rules

| Source | Rule |
|---|---|
| `faq.yaml` "What ages are allowed for public swims?" | "Children under 8 must be accompanied **in the water** by an adult" |
| `faq.yaml` "Are there age restrictions for public swims?" | "Children under 8 must be accompanied by a responsible adult **at all times**" |
| `timetable/templates/timetable/modals/public_swims_faq_modal.html` | states an **under-12** rule that appears nowhere in the FAQ corpus |

"In the water" and "at all times" are materially different obligations, and the
under-12 rule contradicts both. This is a supervision policy on a swimming pool,
so it is the one I would fix first.

**Needed:** the actual rule, and the actual age. I'll then make all three
sources agree.

### Minimum age for lessons

- "What age do lessons begin from?" → "children **over** the age of four"
- "At what age can my child start lessons?" → "four years old **and above**"

These disagree on whether a 4-year-old qualifies.

**Needed:** does a child start at 4, or after their 4th birthday +1 year?

### How move-ups work

- "How do move-ups work?" → assessed on an ongoing basis, moved "depending on
  **space**", mostly at term end
- "How do I move my child to the next level?" → "Progression of levels is decided
  by the **class teacher**"

Both are probably true, but a parent asking one gets a different picture from the
other. They should be one entry, or two that reference each other.

---

## 2. Hardcoded prices — these will drift

Prices are baked into six answers:

| Entry | Prices stated |
|---|---|
| What is a Public Swim? | Adult €6 / Child €4 / Under 3 Free / OAP €3:50 |
| What are Lane Swims? | Adult €6 / OAP €3:50 |
| What are Coached Ladies Lanes? | €7:25 |
| What are Ladies Lessons / Ladies Coached Widths class? | €7:25 |
| What are Coached Lanes? | Adult €7:25 / Teen €5 |
| What are Masters sessions? | €7:25 |

**The bot already has live pricing.** `chatbot/helpers/swim.py` builds a price
table from each product's `price_variants` and passes it to the model. So these
hardcoded figures are a second, un-synchronised source that will silently go
stale the next time prices change — and because a FAQ match short-circuits the
model, the stale figure is what the customer sees.

**Recommendation:** strip the price lines from these six answers and let the live
data answer pricing. **Needed:** your go-ahead, since it changes what customers
are told.

Same issue, smaller: "Do you have aqua aerobics classes?" hardcodes "Tuesday
evening @ 20:35", which the timetable already knows.

---

## 3. Coverage gaps

No entry exists for any of these, and several show up in real traffic:

- **Opening hours** — asked repeatedly; there is no entry at all
- **Contact details** — phone number, email address
- **Parking**
- **Cancellation / refund policy** beyond the two medical/holiday cases
- **Current term dates** (live data exists; a pointer entry would help)
- **How to redeem a coupon / credit note** — the mechanics, not just "yes you can"

From replaying 133 real questions, the most common unanswered themes were
booking mechanics, session times by day, and adult lesson availability.

---

## 4. Duplicate sources of truth still outstanding

Two template files hold **16 hardcoded Q&As** that duplicate the FAQ corpus and
have already drifted from it:

- `timetable/templates/timetable/modals/public_swims_faq_modal.html` (7 Q&As)
- `timetable/templates/timetable/modals/lessons_faq_modal.html` (9 Q&As)

These are maintained by hand, are invisible to the chatbot, and are where the
stray under-12 supervision rule lives.

**Recommendation:** render both modals from `FAQEntry` so there is one source of
truth. **Needed:** confirmation you want the modals to show the same wording the
bot uses.

*(Already removed as dead content: `chatbot/static/chatbot/faq_booking.md`,
referenced by no code, and `chatbot/data/faq.yaml.backup`, a stale 21-entry
snapshot containing its own internal duplicate.)*

---

## 5. What was changed, for the record

**Typos in customer-facing answers:** `receiption`→`reception`, `loggeid`→`logged`,
`advisiided`→`advisable`, `CoachedLanes.suits`→`Coached Lanes. Suits`,
`stepup`→`step up`, `family's`→`families`.

**Stale URL:** an answer linked to
`http://tcsp-morganmck.eu.pythonanywhere.com/accounts/signup/`; now relative,
like every other entry.

**Merged duplicates** (near-identical answers that split the match between them):
- "Do you have family changing rooms?" → merged into "Are there changing facilities?"
- "Can I bring my own toys to public and family swims?" → merged into "Can I bring my own equipment…"
- "Is there a waiting list I can join for Public lessons?" → merged into "Is there a waiting list for lessons?"

**`lessons_only` tagging:** 11 genuinely lesson-internal entries (levels,
move-ups, medical credit, armbands) are now scoped to the lesson bot. The other
58 are shared. Nothing carried this flag before, which is what left the lesson
bot with an empty corpus.

Note the tagging is deliberately narrow: replayed traffic shows the *swim* bot is
asked about lessons constantly ("Are there adult swim lessons?", "How do i book
lessons for my son"), so general lesson questions stay visible to both.
