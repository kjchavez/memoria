# Memoria — Trip Memories Engine

> Date: 2026-02-28
> Status: Draft
> Repo: `github.com/kjchavez/memoria`

---

## Problem

The UK trip page (`invitation.html`) is currently a static invitation. We want to extend it into a living keepsake — a curated journal of the trip's best moments plus a full scrapbook of every photo. Participants should be able to contribute by simply texting photos and messages to a phone number. Everything else is automated.

The infrastructure should be reusable for future trips.

---

## Goals

1. **Zero-friction contribution**: Guests text photos/messages to a number. That's it.
2. **Fully automated curation**: AI organizes, captions, and selects highlights. No human in the loop.
3. **Two views**: A curated day-by-day journal (the main experience) and a filterable scrapbook (everything).
4. **Keepsake**: Exportable to a self-contained static bundle that costs nothing to host forever.
5. **Reusable**: The processing engine works for any trip — UK 2026 is just the first instance.
6. **Infrastructure-as-code**: All GCP resources managed via Terraform. One command to deploy, one to tear down.

---

## Repository Structure

```
memoria/
├── README.md
├── .github/
│   └── workflows/
│       └── ci.yml                  # Lint, test, plan Terraform
│
├── terraform/
│   ├── main.tf                     # Provider config, backend
│   ├── variables.tf                # Project ID, region, Twilio creds, etc.
│   ├── outputs.tf                  # Webhook URL, bucket name, etc.
│   ├── cloud_run.tf                # Webhook service + batch job
│   ├── storage.tf                  # GCS bucket
│   ├── firestore.tf                # Firestore database + indexes
│   ├── scheduler.tf                # Cloud Scheduler for nightly batch
│   ├── iam.tf                      # Service accounts + permissions
│   ├── secrets.tf                  # Secret Manager (Twilio, Claude API keys)
│   ├── terraform.tfvars.example    # Example variable values
│   └── environments/
│       ├── dev.tfvars              # Dev/test project settings
│       └── prod.tfvars             # Production project settings
│
├── src/
│   ├── webhook/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                 # Flask app: Twilio webhook endpoint
│   │   ├── twilio_handler.py       # Parse incoming SMS/MMS, validate sender
│   │   ├── storage.py              # Save media to GCS
│   │   └── firestore.py            # Write incoming records
│   │
│   ├── batch/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                 # Entry point for nightly batch job
│   │   ├── exif.py                 # EXIF extraction + geocoding
│   │   ├── resize.py               # Image resizing (Pillow)
│   │   ├── analyze.py              # Claude vision API calls
│   │   ├── curate.py               # Journal curation logic
│   │   ├── manifest.py             # Build + write manifest.json
│   │   └── dedup.py                # Near-duplicate detection
│   │
│   ├── export/
│   │   ├── requirements.txt
│   │   ├── export.py               # Download from GCS, bake into static bundle
│   │   └── templates/
│   │       └── keepsake.html       # Self-contained HTML template
│   │
│   └── shared/
│       ├── config.py               # Trip config loader (from Firestore)
│       ├── models.py               # Data models (Trip, Participant, Message, Photo)
│       └── gcs.py                  # GCS helper utilities
│
├── frontend/
│   ├── memories.js                 # Journal + scrapbook rendering component
│   ├── memories.css                # Styles for journal/scrapbook views
│   └── lightbox.js                 # Photo lightbox with navigation
│
├── trips/
│   └── uk-2026/
│       ├── trip.yaml               # Trip config: dates, destination, locations, participants
│       ├── invitation.html         # Bespoke invitation page (imports frontend/memories.js)
│       └── itinerary.json          # Day-by-day plan for AI context
│
├── scripts/
│   ├── create_trip.py              # CLI: create a new trip from a YAML config
│   ├── register_participant.py     # CLI: add a participant to a trip
│   ├── run_batch.py                # CLI: manually trigger batch processing
│   ├── export_trip.py              # CLI: export a trip to static bundle
│   └── simulate/
│       ├── send_test_messages.py   # Synthetic test: send fake photos/texts to Twilio
│       └── fixtures/
│           ├── sample_photos/      # Sample images for synthetic testing
│           └── test_messages.json  # Scripted sequence of test messages
│
├── tests/
│   ├── test_webhook.py             # Unit tests for webhook handler
│   ├── test_exif.py                # Unit tests for EXIF extraction
│   ├── test_curate.py              # Unit tests for curation logic
│   ├── test_manifest.py            # Unit tests for manifest building
│   └── test_integration.py         # Integration test: end-to-end with emulators
│
├── pyproject.toml                  # Python project config (uv/pip)
└── .env.example                    # Required env vars
```

---

## Architecture

Three cleanly separated layers:

### 1. The Engine (reusable, lives across trips)

| Component | Service | Purpose |
|-----------|---------|---------|
| SMS/MMS ingestion | Twilio (one phone number) | Receives photos and text messages from participants |
| Webhook handler | Cloud Run service (Python/Flask) | Receives Twilio webhooks, stores raw media, writes to Firestore |
| Batch processor | Cloud Run Job + Cloud Scheduler | Nightly AI analysis, curation, and manifest generation |
| AI | Claude API (vision + text) | Captioning, quality scoring, day summaries, curation |
| Secrets | GCP Secret Manager | Twilio auth token, Claude API key |

The Twilio number is reused across trips. Incoming messages are routed to the "active trip" based on a participant registry in Firestore.

### 2. Trip Data (per-trip, stored in GCS)

```
gs://memoria-{project-id}/
  uk-2026/
    raw/              # Original photos as received
    processed/
      large/          # 1600px resized
      thumb/          # 400px thumbnails
    manifest.json     # Complete structured output for the frontend
```

Firestore collections:

```
trips/{trip_id}                     # Trip config: dates, destination, timezone, status
trips/{trip_id}/participants/{id}   # name, phone number
trips/{trip_id}/messages/{id}       # sender, timestamp, text, mediaUrls, processed
trips/{trip_id}/processing/{id}     # Per-photo analysis results (cached)
```

### 3. Frontend (per-trip, templated)

Each trip gets its own invitation page. The memories rendering is a shared JavaScript component (`frontend/memories.js`) that:
- Fetches `manifest.json` from GCS
- Renders journal view (curated timeline) and scrapbook view (full grid)
- Is dropped into any trip's HTML page with a single `<script>` tag

---

## Infrastructure (Terraform)

### Resources Created

| Resource | Purpose |
|----------|---------|
| Cloud Run Service | Webhook handler (always-on, min 0 instances) |
| Cloud Run Job | Nightly batch processor |
| Cloud Scheduler | Triggers batch job (configurable schedule per trip timezone) |
| GCS Bucket | `memoria-{project-id}` — all trip media + manifests |
| Firestore Database | Trip configs, participant registry, message queue |
| Secret Manager Secrets | `twilio-auth-token`, `claude-api-key` |
| Service Accounts | `memoria-webhook@` (Cloud Run), `memoria-batch@` (Cloud Run Job) |
| Artifact Registry | Docker images for webhook + batch services |
| IAM Bindings | Least-privilege access for each service account |

### Deploy / Teardown

```bash
# First time setup
cd terraform
cp terraform.tfvars.example terraform.tfvars  # Fill in project ID, region, secrets
terraform init
terraform apply

# Tear down everything
terraform destroy
```

### Environments

Two tfvars files for dev vs. prod:
- `dev.tfvars`: points at a test GCP project, uses test Twilio number
- `prod.tfvars`: points at production GCP project, uses real Twilio number

Same Terraform code, different variable values.

---

## Processing Pipeline

### Ingestion (real-time, lightweight)

Triggered by Twilio webhook on each incoming SMS/MMS.

1. Cloud Run endpoint receives the webhook
2. Validates sender against participant registry (rejects unknown numbers)
3. Downloads media from Twilio's URL, saves to `gs://memoria-{project}/raw/{trip_id}/{timestamp}_{sender}.{ext}`
4. Writes a record to Firestore `trips/{trip_id}/messages` collection:
   - `sender`: phone number
   - `senderName`: looked up from participant registry
   - `timestamp`: message timestamp
   - `text`: any accompanying text (or the full message if text-only)
   - `mediaUrls`: list of GCS paths for attached images
   - `processed`: false
5. Sends SMS reply: "Got it!" (or rotating fun responses)

Processing time: under 1 second. No heavy work here.

### Nightly Batch Job

Runs via Cloud Scheduler at 2 AM local trip time. Processes all records where `processed: false`.

**Step 1 — Extract & Enrich**

- Extract EXIF data: GPS coordinates, timestamp, camera/device info
- Reverse-geocode GPS to location name (Google Maps Geocoding API or a simple lookup table of known trip locations from `trip.yaml`)
- Match timestamp to trip day (Day 1 = May 21, Day 2 = May 22, etc.)
- Resize images: generate 1600px (large) and 400px (thumbnail) versions
- Store processed images in `gs://trip/processed/large/` and `gs://trip/processed/thumb/`

**Step 2 — AI Analysis (Claude vision)**

For each photo, send to Claude with trip context:

```
This is a photo from Day {N} of a trip to {destination}.
Today's planned locations: {locations from itinerary}.
The photo was taken at {time} near {reverse-geocoded location}.
It was sent by {sender name}.

Please provide:
1. A natural, warm caption (1-2 sentences)
2. Activity category: sightseeing | food | sports | nature | group | transport | nightlife
3. Quality score 1-10 (composition, sharpness, visual interest)
4. Brief description for accessibility (alt text)
```

For text-only messages, classify as: quote, reaction, or story snippet.

**Step 3 — Curate the Journal**

- Group all items by day
- Within each day, cluster by time proximity and location
- For each cluster, select top 2-3 photos by quality score, prioritizing variety (different subjects, different people)
- Detect near-duplicates (bursts of similar shots) and keep only the best
- Select one hero photo per day (highest quality, most representative)
- Arrange into narrative arc: morning → afternoon → evening
- Place text messages chronologically as pull-quotes
- Generate a 2-3 sentence day summary via Claude, given the selected photos and their captions

**Step 4 — Build the Manifest**

Write `manifest.json` to GCS:

```json
{
  "trip": {
    "id": "uk-2026",
    "title": "England 2026",
    "dates": { "start": "2026-05-21", "end": "2026-05-28" },
    "participants": ["Elizabeth", "Jessica", "Kevin", "Grant"]
  },
  "days": [
    {
      "date": "2026-05-22",
      "dayNumber": 2,
      "label": "Day 2 — Fri, May 22",
      "title": "Theatre Night",
      "summary": "Borough Market for brunch, the Globe in the afternoon, then the main event — Aidan Turner live on stage at the National Theatre.",
      "journal": [
        {
          "type": "photo",
          "url": "processed/large/20260522_143022_elizabeth.jpg",
          "thumb": "processed/thumb/20260522_143022_elizabeth.jpg",
          "caption": "The view from the Globe Theatre's upper gallery — the Thames glinting in the afternoon sun.",
          "alt": "View from Shakespeare's Globe Theatre looking out over the Thames river",
          "by": "Elizabeth",
          "time": "14:30",
          "location": "Shakespeare's Globe",
          "category": "sightseeing",
          "quality": 8
        },
        {
          "type": "quote",
          "text": "This cream tea is incredible",
          "by": "Jessica",
          "time": "16:15"
        }
      ],
      "scrapbook": [
        {
          "url": "processed/large/20260522_101512_kevin.jpg",
          "thumb": "processed/thumb/20260522_101512_kevin.jpg",
          "caption": "Stacked wheels of cheese at Borough Market.",
          "alt": "Display of artisan cheese wheels at Borough Market stall",
          "by": "Kevin",
          "time": "10:15",
          "location": "Borough Market",
          "category": "food",
          "quality": 6
        }
      ]
    }
  ]
}
```

Mark all processed records in Firestore as `processed: true`.

---

## Frontend Rendering

### Page Lifecycle

| Phase | When | What shows |
|-------|------|------------|
| Pre-trip | Now → May 20 | Invitation: hero, overview, map, highlights, timeline (the plan), packing |
| During trip | May 21-28 | Completed days show memories in the timeline; future days still show the plan |
| Post-trip | May 29+ | Journal becomes the main event; invitation sections become a nostalgic header |

### Journal View (default)

Extends the existing timeline design. Each day's card expands from a plan description to a photo-rich journal entry:

- **Hero photo**: the single best shot of the day, displayed large at the top of the card
- **Supporting photos**: 2-3 additional photos in a row beneath
- **AI day summary**: replaces the planned description with what actually happened
- **Pull-quotes**: text messages styled as italic callout blocks with sender attribution
- Scrolls as one continuous story from Day 1 through Day 8

Uses the existing timeline CSS — same alternating layout, gold dots, cards, hover effects.

### Scrapbook View

Toggled via a button in the nav. Full masonry grid of every photo received.

Filter chips across the top:
- By day: `Day 1` `Day 2` `Day 3` ...
- By person: `Elizabeth` `Jessica` `Kevin` `Grant`
- By location: `Borough Market` `Selhurst Park` `Botallack` ...

Click a photo for a lightbox: full-size image, caption, who sent it, when and where. Arrow keys / swipe to navigate.

### Implementation

All client-side vanilla JavaScript. On page load:
1. Fetch `manifest.json` from GCS (or embedded in the page post-export)
2. Determine page phase (pre-trip, during, post-trip) based on current date
3. Render the appropriate view

No framework. Consistent with the existing codebase (vanilla JS, Leaflet map, CSS animations).

---

## Export & Keepsake

After the trip, when all photos are processed and the journal is complete, run an export:

**Export script** (`scripts/export_trip.py`):

```bash
python scripts/export_trip.py --trip uk-2026 --output ./export/uk-2026-keepsake/
```

1. Downloads all processed images from GCS
2. Downloads `manifest.json`
3. Rewrites image URLs in the manifest to relative paths (`assets/large/...`, `assets/thumb/...`)
4. Copies the trip's `invitation.html` and embeds the manifest as a `<script>` block
5. Bundles the frontend component (`memories.js`, `memories.css`, `lightbox.js`)
6. Outputs a self-contained directory:

```
uk-2026-keepsake/
  index.html          # Complete page with embedded manifest + JS/CSS
  assets/
    large/            # Full-size photos
    thumb/            # Thumbnails
```

**Result**: A folder that works anywhere — GitHub Pages, any static host, a USB drive, or just opened as a local file in a browser.

**Post-export cleanup**:
- Deactivate trip in Firestore (Twilio number freed for next trip)
- Optionally delete raw images from GCS (processed ones are in the export)
- Keep the export bundle on GCS in a cold storage bucket (pennies/year)

---

## Testing Strategy

### Synthetic Test

A script (`scripts/simulate/send_test_messages.py`) that simulates a 2-day fake trip:

1. Reads `fixtures/test_messages.json` — a scripted sequence of SMS/MMS events with timestamps and sample photos
2. Sends them to the Twilio number via the Twilio API (as if from registered test participants)
3. Triggers the batch job manually via `scripts/run_batch.py`
4. Validates the output manifest against expected structure
5. Opens the rendered page for visual inspection

Can run against the dev environment at any time. Useful during development and as a CI smoke test.

**Fixture example** (`test_messages.json`):

```json
[
  { "from": "+15551234567", "body": "Just landed!", "media": null, "delay_seconds": 0 },
  { "from": "+15551234567", "body": "First pub!", "media": "fixtures/sample_photos/pub.jpg", "delay_seconds": 30 },
  { "from": "+15559876543", "body": null, "media": "fixtures/sample_photos/bridge.jpg", "delay_seconds": 60 },
  { "from": "+15559876543", "body": "This view is unreal", "media": "fixtures/sample_photos/sunset.jpg", "delay_seconds": 120 }
]
```

### Live Smoke Test

Before the UK trip, do a real 1-day "test trip":

1. Create a test trip via `scripts/create_trip.py` with today's date
2. Register yourself (and optionally others) as participants
3. Go about your day, text real photos to the number
4. Let the batch job run overnight
5. Check the rendered page the next morning

This validates the entire end-to-end flow with real phones, real photos, real EXIF data.

### Unit Tests

Standard pytest suite covering:
- Webhook request parsing and validation
- EXIF extraction from sample images
- Curation logic (clustering, dedup, selection)
- Manifest schema validation
- Firestore read/write (using Firestore emulator)

---

## Spinning Up a New Trip

```bash
# 1. Write a trip config
cat > trips/my-trip/trip.yaml << EOF
id: my-trip
title: "My Trip"
destination: "Iceland"
dates:
  start: 2026-08-01
  end: 2026-08-07
timezone: Atlantic/Reykjavik
locations:
  - name: Reykjavik
    lat: 64.1466
    lng: -21.9426
  - name: Blue Lagoon
    lat: 63.8804
    lng: -22.4495
participants:
  - name: Kevin
    phone: "+15551234567"
  - name: Grant
    phone: "+15559876543"
EOF

# 2. Create the trip in Firestore
python scripts/create_trip.py --config trips/my-trip/trip.yaml

# 3. Customize the invitation page (optional, bespoke per trip)

# 4. Done — participants can start texting photos
```

The engine code doesn't change. Each trip is just configuration + data.

---

## Cost Estimates

### During a trip (~1 week active)

| Service | Estimate | Notes |
|---------|----------|-------|
| Twilio SMS/MMS | $5-15 | ~$0.0079/SMS + $0.01/MMS received, maybe 100-200 messages |
| Cloud Run | $1-3 | Webhook handler + nightly job, minimal compute |
| GCS | < $1 | A few GB of photos |
| Claude API | $5-15 | Vision analysis of ~200 photos + day summaries |
| Google Maps Geocoding | < $1 | Reverse geocoding, ~200 calls |
| **Total** | **~$12-35** | For the entire trip |

### After export

| Service | Estimate | Notes |
|---------|----------|-------|
| Static hosting | $0 | GitHub Pages (free) or GCS static site (~$0.01/month) |
| Cold storage backup | < $0.10/year | GCS Coldline for the raw bundle |

---

## Open Questions

- **Participant authentication**: Should the system only accept messages from registered phone numbers, or allow anyone to text in? (Recommendation: registered only, to avoid spam and enable sender attribution.)
- **Photo moderation**: Is any content filtering needed, or is this a trusted small group? (Recommendation: skip for now, trusted group.)
- **Multiple active trips**: Support concurrent trips with different participant groups? (Recommendation: not now, but the data model supports it — just route by sender phone.)
- **Video**: Should the system handle short video clips too? (Adds complexity to processing and storage. Recommendation: photos + text only for v1.)

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Infrastructure-as-code | Terraform |
| SMS/MMS | Twilio |
| Webhook handler | Cloud Run (Python / Flask) |
| Batch processing | Cloud Run Jobs + Cloud Scheduler |
| AI | Claude API (vision + text) |
| Storage | Google Cloud Storage |
| Database | Firestore |
| Secrets | GCP Secret Manager |
| Container registry | GCP Artifact Registry |
| Geocoding | Google Maps Geocoding API |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| Hosting | GitHub Pages (or GCS static site) |
| Testing | pytest + Firestore emulator + Twilio test credentials |
| CI | GitHub Actions |
