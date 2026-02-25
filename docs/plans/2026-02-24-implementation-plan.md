# Implementation Plan: AidSec Dashboard Optimization

This document breaks down the implementation of the "Intelligent Campaign Engine" (Masterplan) into specific, actionable development phases.

## Phase 1: Data Architecture & Scraper Foundation

**Goal:** Establish the database schema for the new enrichment data and build the tools to collect information autonomously.

### Step 1.1: Database Schema Expansion

- **File:** `aidsec_dashboard/database/models.py`
- **Action:**
  - Create a new SQLAlchemy model `LeadEnrichment`.
    - Fields: `id`, `lead_id` (ForeignKey, unique=True), `about_us` (Text), `mission_statement` (Text), `services_offered` (JSON), `ssl_valid` (Boolean), `ssl_issuer` (String), `dns_sec` (Boolean), `cms_detected` (String).
  - Add a `1:1` relationship in the `Lead` model: `enrichment = relationship("LeadEnrichment", back_populates="lead", uselist=False, cascade="all, delete-orphan")`.

### Step 1.2: Build the `scraper_service.py`

- **File:** `aidsec_dashboard/services/scraper_service.py`
- **Action:**
  - Create a service that takes a URL, visits the homepage and attempts to find an "About Us" or "Team" page.
  - Extract meaningful paragraphs (filtering out headers/footers) to summarize the company's mission and core offerings.
  - Handle timeouts and anti-bot protection gracefully (returning `None` if blocked).

### Step 1.3: Enhance `ranking_service.py`

- **File:** `aidsec_dashboard/services/ranking_service.py`
- **Action:**
  - Import python `ssl` and `socket` to connect to the domain and verify the SSL certificate validity and issuer.
  - Add basic footprinting for WordPress (checking for `/wp-includes/` or `wp-content` in the HTML source).
  - Return these new data points alongside the standard Header grade.

## Phase 2: Background Tasks & Autonomous Ingestion

**Goal:** Ensure that whenever a lead is created, it is automatically enriched without blocking the UI.

### Step 2.1: The Enrichment Worker

- **File:** `aidsec_dashboard/api/routes/leads.py` & `aidsec_dashboard/services/enrichment_service.py`
- **Action:**
  - Build `enrichment_service.py` to orchestrate `scraper_service` and `ranking_service`.
  - Update the `POST /api/leads` and Excel/CSV import routes to trigger `BackgroundTasks.add_task(enrichment_service.enrich_lead, lead_id)`.
  - Add a `POST /api/leads/{id}/enrich` endpoint to trigger enrichment manually for existing leads.

## Phase 3: Smart Campaign Engine & AI Generator Update

**Goal:** Automate the AI drafting process so that it utilizes the new enrichment data and creates drafts for human review.

### Step 3.1: Update the LLM Prompt

- **File:** `aidsec_dashboard/services/llm_service.py`
- **Action:**
  - Fetch `LeadEnrichment` data if it exists for the lead.
  - Update the `generate_outreach_email` prompt to instruct the AI to reference the company's specific mission/services, the status of their SSL, and any CMS vulnerabilities found.

### Step 3.2: Automated Draft Generation (Campaigns)

- **File:** `aidsec_dashboard/api/routes/campaigns.py` or a dedicated background scheduler.
- **Action:**
  - When a campaign triggers a step for a lead, instead of just logging it, generate the email via `llm_service.py`.
  - Save the generated email in `EmailHistory` with the status `EmailStatus.DRAFT`, linked to the `campaign_id` and `lead_id`.

## Phase 4: Frontend "Drafts for Review" View (Human-in-Loop)

**Goal:** Give the team a centralized UI to approve or edit the AI's drafts.

### Step 4.1: API Endpoint for Drafts

- **File:** `aidsec_dashboard/api/routes/emails.py`
- **Action:**
  - Create `GET /api/emails/drafts` to fetch all `EmailHistory` items where `status == "draft"`, including the joined `Lead` data.

### Step 4.2: Next.js Frontend UI

- **Files:** `frontend/src/app/(dashboard)/drafts/page.tsx`
- **Action:**
  - Create a clean list/inbox view showing all pending drafts.
  - Include a "Review" button that opens a modal with a text editor to modify the draft.
  - Include checkboxes to bulk-select leads and hit "Approve & Send" (updating status to `SENT` and dispatching via `email_service.py`).

## Phase 5: The Reply Handler

**Goal:** Detect when prospects reply to halt further automated follow-ups.

### Step 5.1: Webhook / IMAP Listener

- **File:** `aidsec_dashboard/api/routes/webhooks.py`
- **Action:**
  - Create an endpoint (e.g., `/api/webhooks/brevo/inbound`) to receive inbound email events.
  - Match the inbound email address to a `Lead`.
  - Update the Lead status to `PENDING` (needs human attention) and pause any active `CampaignLead` entries for that lead.
