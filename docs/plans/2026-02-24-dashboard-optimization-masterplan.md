# Masterplan: AidSec Dashboard Optimization (AI SDR & Smart Campaign Engine)

## Executive Summary

The vision is to evolve the AidSec Lead Management Dashboard from a passive CRM into an **Intelligent Campaign Engine**. It will operate with a "Human-in-the-Loop" architecture initially, prioritizing high-volume outreach (Approach C) powered by deep, AI-driven personalization (Approach A). Once the team trusts the automated decision-making and AI email outputs, the system will easily transition into a fully autonomous agent.

## Core Architecture & Data Flow

### 1. Ingestion & Auto-Enrichment (The "Scraper Node")

When a lead is imported or manually added:

- A background task instantly triggers an enrichment pipeline.
- **Action:** The system automatically scrapes the Lead's website (for "About Us", mission, and tone) and runs the `ranking_service` (Security Headers, DNS, basic SSL checks).
- **Storage:** Data is stored in a structured `LeadEnrichment` table to keep the core `Lead` model clean and allow for easy expansion (e.g., adding LinkedIn scraping later).

### 2. The Smart Campaign Engine

Leads are assigned to automated Campaigns (e.g., "Medical Practices April").

- Campaigns operate on strict step-intervals (e.g., Day 1, Day 3, Day 7).
- **Action:** When a lead hits an active day, the **AI Email Generator** triggers automatically.
- It consumes the `LeadEnrichment` data to write a highly personalized draft, referencing specific security vulnerabilities found on their site and aligning with their company mission.

### 3. The "Drafts for Review" View (Human-in-the-Loop)

Instead of sending emails immediately, drafts land in a new Dashboard UI: **Outgoing Queue**.

- **Action:** The user logs in and reviews the AI's personalized text.
- The UI allows for editing individual drafts or bulk-selecting 50+ emails and clicking **"Approve & Send"**.
- _Future State:_ Once the AI's reliability is proven, this queue can be bypassed for "Autonomous Mode."

### 4. The Reply & Interaction Handler

The system must know when to stop messaging.

- **Action:** We will integrate an IMAP listener or Brevo Webhook to detect replies from prospects.
- If a prospect replies, the system instantly flags the lead status as `Replied`, automatically pausing their active campaign to prevent further automated outreach.

## Technical Implementation Priorities

### Phase 1: Foundation & Enrichment

1. **Enhance `ranking_service.py`:** Expand beyond basic headers to include SSL certificate validity and common CMS (WordPress) footprinting.
2. **Create `scraper_service.py`:** Implement a lightweight web scraper (e.g., BeautifulSoup) to extract the "About Us" and primary services from the lead's domain.
3. **Database Migration:** Create the `LeadEnrichment` table and link it to the existing `Lead` model via a 1:1 relationship.

### Phase 2: The Campaign Engine & Drafts Queue

1. **Refactor `campaigns.py`:** Move from a manual trigger system to a background scheduler (e.g., Celery or advanced `BackgroundTasks`) that checks daily for leads due for their next step.
2. **AI Generator Update:** Update the prompt payload in `llm_service.py` to ingest the new enrichment data for hyper-personalized drafts.
3. **Frontend Updates (Next.js):**
   - Create the **Outgoing Queue/Drafts** page.
   - Build the bulk approval workflow.

### Phase 3: Feedback Loop

1. **Reply Detection:** Set up the IMAP/Webhook infrastructure to listen for replies and update the lead status to `Replied` / `Pending`.
2. **Analytics:** Add a "Conversion Health" tab to track open rates, reply rates, and template performance.

## Trade-offs & Considerations

- **Web Scraping Reliability:** Websites vary drastically. The `scraper_service.py` must be fault-tolerant and fail gracefully if a site blocks bots or is malformed. If the scraper fails, the AI must rely on generic (but still professional) template fallbacks.
- **Background Processing:** Running intensive scrapes and LLM generations synchronously will block the API. A robust background task queue is mandatory.

## Testing & Verification

- **Unit Tests:** Ensure the `LeadEnrichment` table creates correctly and links to Leads.
- **Mocked Scrapes:** Create mock HTML responses to verify the `scraper_service.py` extracts data without hitting real websites during testing.
- **End-to-End Workflow:** Manually ingest 3 test leads, verify they auto-enrich, verify they generate drafts on Day 1, and manually approve them through the new UI.
