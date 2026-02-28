# Memoria — Trip Memories Engine

## Overview
Memoria is a reusable trip memories engine. Guests text photos and messages to a Twilio phone number, a nightly batch job uses Claude vision to caption, curate, and organize them, and the results render as a curated journal + scrapbook on a static web page.

## Architecture
- **Webhook handler**: Python/Flask Cloud Run service receives Twilio SMS/MMS webhooks
- **Batch processor**: Python Cloud Run Job runs nightly via Cloud Scheduler
- **Infrastructure**: All GCP resources managed via Terraform
- **Frontend**: Vanilla HTML/CSS/JS — no framework
- **Storage**: GCS for media, Firestore for state
- **AI**: Claude API (vision + text) for captioning and curation

## Key Paths
- `terraform/` — All infrastructure-as-code
- `src/webhook/` — Twilio webhook handler (Cloud Run service)
- `src/batch/` — Nightly batch processor (Cloud Run job)
- `src/export/` — Static keepsake export tool
- `src/shared/` — Shared models, config, GCS utilities
- `frontend/` — Journal + scrapbook JS/CSS components
- `trips/` — Per-trip configs and bespoke invitation pages
- `scripts/` — CLI tools for trip management and testing
- `docs/plans/` — Design documents

## Conventions
- Python 3.12+, use `uv` for dependency management
- Terraform for all GCP infrastructure
- pytest for testing, Firestore emulator for integration tests
- Keep the frontend vanilla JS — no build step, no framework
- Each trip is config + data, the engine code is reusable
