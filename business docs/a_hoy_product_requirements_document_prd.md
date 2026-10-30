# Product Requirements Document (PRD): A-hoy Marketing Solutions

**Document Version:** 1.0  
**Product Model:** Hybrid Software-with-a-Service (SWAS) / Tech-Enabled Agency Platform  
**Target Release:** Phase 1 MVP  

---

## 1. Executive Summary & Product Vision
**A-hoy Marketing Solutions** is a hybrid AI marketing platform and creative agency built for time-strapped small business owners (SMBs). While traditional SaaS tools fail SMBs due to high learning curves and time requirements, and traditional agencies fail due to high retainer costs and slow turnaround times, A-hoy bridges the gap:
1. **The Bridge (Client-Facing Web/Mobile Portal):** A streamlined, zero-clutter monitoring and approval hub where business owners track real-world ROI, approve tailored content in one click, and schedule on-site photo/video shoots.
2. **The Engine Room (Internal Agency + AI Orchestration Backend):** An AI-powered production pipeline that transforms raw photo/video shoots into 30–90 days of omnichannel campaigns, automates review responses, and manages local lead generation.

---

## 2. Target Audience & User Personas

| Persona | Role | Core Pain Points | Key Jobs-to-be-Done (JTBD) |
| :--- | :--- | :--- | :--- |
| **The Time-Poor Owner** *(Primary Client)* | Local SMB Owner (Optometry/Dental Clinics, Home Services, Cafes, Retail) | No time to post on social media, respond to Google reviews, or learn Meta Ads Manager; skeptical of vague agency metrics. | See exact revenue/leads generated, approve authentic content in under 3 minutes/month, and request flash promos easily. |
| **The Account Captain** *(Internal Agency User)* | A-hoy Account Manager / Marketing Strategist | Managing 30+ SMB accounts manually causes burnout and quality drops. | Use AI to slice raw media, generate localized copy, schedule omnichannel posts, and push batches to clients for sign-off. |
| **The Field Creator** *(Contractor/Staff)* | Local Photographer / Videographer | Unclear client expectations during on-site shoots; disorganized file handoffs. | View AI-generated shot lists before arriving on-site and upload raw footage directly into the client's cloud vault. |

---

## 3. Functional Requirements & Feature Specifications

### 3.1. Client-Facing Portal ("The Bridge")

| Feature ID | Feature Name | Priority | Description & Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **CL-01** | **The "Treasure Map" ROI Dashboard** | **P0 (MVP)** | • Displays top-line business metrics: *Estimated Revenue Generated, Total Leads (Calls + Forms), New Reviews, and Ad Spend.*<br>• Integrates with Google Business Profile, Meta/Google Ads, call-tracking numbers (Twilio), and POS/booking APIs (Square, Clover, Stripe).<br>• Hides vanity metrics (CTR, impressions) behind an optional "Detailed View" toggle. |
| **CL-02** | **One-Click Content Approval Queue** | **P0 (MVP)** | • Presents upcoming social posts, short-form videos (Reels/TikToks), and email blasts in a card-stack or grid interface.<br>• Clients can **Approve**, **Request Edit** (via voice note or text comment), or **Swap Media** from their Asset Vault.<br>• Auto-publishes approved items at scheduled times; sends SMS/push reminder 48 hours before queue expiration. |
| **CL-03** | **On-Site Shoot Scheduler & Prep** | **P1** | • Allows Cruiser/Flagship tier clients to book their monthly/quarterly 90-minute photo/video shoot via calendar integration.<br>• Generates an automated pre-shoot checklist for the client (e.g., *"Have 3 products ready and 1 staff member available for a 2-minute Q&A"*). |
| **CL-04** | **"Flare Gun" Instant Promo Trigger** | **P1** | • A prominent quick-action button on mobile/desktop where the owner inputs a plain-English request (e.g., *"We have 4 open eye exam slots tomorrow—run a promo"*).<br>• Automatically alerts the Engine Room, pulls relevant client media from the vault, drafts an SMS/social blast, and returns a preview for client approval within 60 minutes. |
| **CL-05** | **Review & Reputation Radar** | **P0 (MVP)** | • Aggregates Google, Yelp, and Facebook reviews in one feed.<br>• Auto-replies to 4- and 5-star reviews using brand-voice AI (with optional 24-hour delay).<br>• Flags 1- to 3-star reviews via SMS alert to the owner with a pre-drafted empathetic response for one-click approval. |

### 3.2. Agency + AI Backend ("The Engine Room")

| Feature ID | Feature Name | Priority | Description & Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **AG-01** | **Client Brand Brain (RAG Context)** | **P0 (MVP)** | • Stores structured brand profiles per client: tone of voice, services/menus, pricing, target zip codes, seasonal offers, and compliance constraints (e.g., healthcare/optometry disclaimers).<br>• All LLM prompts dynamically inject this context to prevent generic output. |
| **AG-02** | **AI Media Multiplier Pipeline** | **P0 (MVP)** | • Ingests raw video and photo files from on-site shoots or client phone uploads.<br>• Automatically transcribes video, removes dead air, slices long videos into 15–30 second vertical clips, applies dynamic captions, and tags assets by category (*staff, exterior, product, testimonial*). |
| **AG-03** | **Omnichannel Campaign Generator** | **P0 (MVP)** | • Pairs tagged visual assets from the vault with AI-generated captions, local SEO keywords, and hashtags.<br>• Outputs formatted variations for Instagram, Facebook, TikTok, Google Business Profile updates, and monthly email newsletters in a single batch. |
| **AG-04** | **AI Pre-Shoot Shot List Generator** | **P2** | • Analyzes top-performing local competitor content and seasonal trends in the client's niche.<br>• Generates a structured 90-minute shot list and interview script for the Field Creator 48 hours prior to a scheduled shoot. |

---

## 4. End-to-End System Architecture & Tech Stack
* **Frontend (Client Portal & Internal Admin):** Next.js (React), TypeScript, Tailwind CSS, deployed on Vercel or Azure App Service (with Progressive Web App / PWA support for mobile install).
* **Backend & Database:** Python (FastAPI) + PostgreSQL (via Supabase or Azure Database for PostgreSQL) with `pgvector` for storing client Brand Brain embeddings.
* **Cloud Storage & Media CDN:** Azure Blob Storage or AWS S3 + Mux / Cloudinary API for automated video transcoding, auto-cropping, and thumbnail generation.
* **AI & Orchestration Layer:**
  * **Text & Strategy:** OpenAI GPT-4o / Claude 3.5 Sonnet for brand-voice copywriting, review responses, and "Flare Gun" campaign parsing.
  * **Audio/Video Processing:** Whisper API (transcription & timestamping) + FFmpeg / Submagic API for automated vertical slicing and burned-in captions.
* **Third-Party Integrations:**
  * **Social & Local Publishing:** Ayrshare API or Meta Graph API / TikTok API / Google Business Profile API.
  * **Communications & Call Tracking:** Twilio (SMS alerts, missed-call text-back, tracked phone numbers).
  * **Payments & Subscriptions:** Stripe Billing (recurring tier management + ad spend pass-through).

---

## 5. UI Wireframes: Client Portal ("The Bridge")

### 5.1. Main Dashboard & Approval View

```text
+-------------------------------------------------------------------+
| ⚓ A-HOY BRIDGE          [Oak Lawn Optometry ▾]     [🚨 FLARE GUN] |
+-------------------------------------------------------------------+
|                                                                   |
|  🗺️ OCTOBER TREASURE MAP (ROI SUMMARY)                            |
|  +-------------------+ +-------------------+ +-----------------+  |
|  | 💰 $11,400        | | 📞 38 New Leads   | | ⭐ +14 Reviews  |  |
|  | Est. Revenue      | | (29 Calls, 9 Web) | | 4.9 Avg Rating  |  |
|  +-------------------+ +-------------------+ +-----------------+  |
|                                                                   |
|-------------------------------------------------------------------|
|  📋 CONTENT READY FOR INSPECTION (4 Left in Batch)   [Approve All]|
|                                                                   |
|  +-------------------------------------------------------------+  |
|  | [📱 Instagram Reel / TikTok]       Scheduled: Tue, Nov 3 9AM|  |
|  | +-------------------------+  Caption:                       |  |
|  | |                         |  "Did you know your FSA dollars |  |
|  | |     [ VIDEO PLAYER ]    |   expire Dec 31st? 👓 Stop by   |  |
|  | |   0:22 Vertical Clip    |   our Oak Lawn clinic this week |  |
|  | |  (Dr. Nguyen + Frames)  |   to use your benefits on..."   |  |
|  | |       ▶️ Play Clip      |                                 |  |
|  | +-------------------------+  🏷️ Asset: Oct_Shoot_Clip_04.mp4|  |
|  |                                                             |  |
|  |   [ ✅ Approve Post ]   [ ✏️ Request Edit ]   [ 🔄 Swap Pic ] |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
|-------------------------------------------------------------------|
|  📸 NEXT ON-SITE MEDIA SHOOT                    ⚙️ REPUTATION RADAR|
|  +-------------------------------------------+  +--------------+  |
|  | 📅 Thu, Nov 12 @ 2:00 PM (90 Mins)        |  | 5★ Auto-Sent |  |
|  | Creator: Marcus V.                        |  | 12 Replies   |  |
|  | [View AI Shot List]   [Reschedule Shoot]  |  | 1 Needs Look |  |
|  +-------------------------------------------+  +--------------+  |
+-------------------------------------------------------------------+
|  [ 🏠 Home ]     [ 🗓️ Calendar ]     [ 🗄️ Media Vault ]   [ ⭐ Reviews ]|
+-------------------------------------------------------------------+
```

### 5.2. The "Flare Gun" Modal (15-Second Promo Trigger)

```text
+-------------------------------------------------------------------+
| 🚨 FIRE A FLARE (INSTANT CAMPAIGN)                            [X] |
+-------------------------------------------------------------------+
| Tell your AI First Mate what you need promoted right now:         |
|                                                                   |
| +---------------------------------------------------------------+ |
| | "We just had 3 cancellations for tomorrow afternoon. Let's    | |
| |  offer $50 off a complete pair of prescription sunglasses     | |
| |  for anyone who books a Friday slot."                         | |
| +---------------------------------------------------------------+ |
| [ 🎙️ Hold to Speak Voice Note ]                                   |
|                                                                   |
| Channels to Fire:                                                 |
| [x] Instagram/FB Story   [x] SMS Win-Back List   [x] Google Update|
|                                                                   |
|           [ 🚀 Generate & Send Preview in < 30 Mins ]             |
+-------------------------------------------------------------------+
```

---

## 6. Core MVP User Stories & Acceptance Criteria

### Epic 1: Frictionless Content Approval (`CL-02`)
* **User Story 1.1 (Passwordless Magic Link Approval):**
  * *As a* busy small business owner,
  * *I want to* tap an SMS link when my monthly content batch is ready and go straight to my approval queue without typing a password,
  * *So that* I can approve 30 days of marketing while waiting for my morning coffee.
  * **Acceptance Criteria:**
    * Clicking the Twilio SMS link authenticates the user via a signed, short-lived JWT token (valid for 48 hours).
    * Swiping right or tapping **[✅ Approve Post]** transitions `content_queue.status` from `pending_client` to `approved` and loads the next card in $< 200\text{ ms}$.
* **User Story 1.2 (Voice/Text Revision Loop):**
  * *As a* client reviewing a post,
  * *I want to* tap **[✏️ Request Edit]** and leave a 10-second voice note or quick text comment,
  * *So that* the AI or my Account Captain fixes the caption without me having to rewrite it myself.
  * **Acceptance Criteria:**
    * Submitting feedback sets `status = 'changes_requested'` and triggers a webhook that passes `client_feedback` + `brand_profiles` to the LLM to immediately propose an updated caption, or flags the Account Captain in the internal Engine Room.

### Epic 2: Closed-Loop ROI Visibility (`CL-01`)
* **User Story 2.1 (Plain-English Revenue Estimator):**
  * *As a* small business owner skeptical of marketing agencies,
  * *I want to* see an estimated dollar value of revenue generated at the top of my dashboard,
  * *So that* I immediately know my monthly retainer is paying for itself.
  * **Acceptance Criteria:**
    * If POS integration is active, display exact `SUM(pos_attributed_revenue_usd)` for the current billing period.
    * If POS integration is not yet connected, calculate estimated revenue dynamically:
      $$\text{Estimated Revenue} = (\text{Tracked Calls over 60s} + \text{Form Leads}) \times \text{Client Conversion Rate (Default } 25\%) \times \text{client.average\_ticket\_value}$$
    * Clicking the revenue card opens a transparent breakdown showing the exact call recordings/logs and form submissions that made up the number.

### Epic 3: Internal AI Media Multiplier (`AG-02`)
* **User Story 3.1 (Batch Upload to Draft Queue):**
  * *As an* Account Captain managing 30 small business accounts,
  * *I want to* drag and drop a folder of 20 raw photos and 5 raw videos from an on-site shoot into a client's vault and click *"Generate 30-Day Plan"*,
  * *So that* the system automatically pairs visuals with brand-accurate captions and populates the draft calendar in under 5 minutes.
  * **Acceptance Criteria:**
    * Video files trigger an async worker (Celery/FastAPI background task) that extracts audio via FFmpeg, transcribes via Whisper, identifies 15–30s hook segments, crops to 9:16 vertical, and saves new rows in `media_assets` with `asset_type = 'sliced_reel'`.
    * Vision LLM inspects each photo/video thumbnail, assigns `ai_tags`, and creates 12–20 scheduled entries in `content_queue` (`status = 'draft_internal'`) spaced evenly across the next 30 days.

---

## 7. Phased Rollout Roadmap & KPIs

### Phased Rollout
* **Phase 1: Concierge MVP (Months 1–2):** Validate with 5–10 local pilot clients. Build the Client Portal (`CL-01`, `CL-02`, `CL-05`) and use semi-automated Python scripts in the backend to run the Brand Brain (`AG-01`) and Campaign Generator (`AG-03`).
* **Phase 2: Scalable Automation (Months 3–4):** Launch the automated AI Media Multiplier Pipeline (`AG-02`), Flare Gun Trigger (`CL-04`), and Shoot Scheduler (`CL-03`).
* **Phase 3: Full Ecosystem & POS Attribution (Months 5–6):** Direct POS/CRM integrations (Square, Clover, practice management software) and automated Meta & Google Local Services Ad launching.

### Key Performance Indicators (KPIs)
* **Client Engagement:** Average Time-to-Approve Monthly Content Batch $< 48\text{ hours}$ from push notification.
* **Operational Efficiency:** Internal Agency Fulfillment Time per Client $< 60\text{ minutes/month}$ (excluding on-site shoot).
* **Product Stickiness:** Monthly Client Portal Active Login / SMS Interaction Rate $> 85\%$.
* **Business Health:** Monthly Logo Churn Rate $< 4\%$; Blended Gross Margin $> 70\%$.