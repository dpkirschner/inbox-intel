Of course. This is a fantastic evolution of the original idea. Using the Guesty API instead of parsing emails makes the entire system more robust, reliable, and powerful.

Here is the rewritten Product Requirements Document (PRD) for "InboxIntel," now architected around the Guesty API.

***

### **Product Requirements Document (PRD)**

**Project:** InboxIntel

**Version:** v2.0 (Guesty API Edition)
**Last updated:** {{DATE}}

---

### 1. Overview

InboxIntel is a self-hosted service that connects directly to your Guesty account via its official API. It monitors guest messages in real-time, classifies them using an LLM, and automatically alerts you about important requests such as early check-ins or late check-outs. It can also generate daily or on-demand reports that summarize current reservations and flag special accommodations, providing a centralized intelligence layer for your hosting operations.

---

### 2. Goals & Objectives

| Goal | Description |
| :--- | :--- |
| **Automate message monitoring** | Ingest all guest messages directly from Guesty in real-time without manual review. |
| **Detect actionable messages** | Identify guest requests such as early check-in or late check-out using natural language understanding. |
| **Deliver timely notifications** | Send instant push notifications to your phone when a message needs attention. |
| **Provide daily summaries** | Generate a digest of today’s reservations, guest names, and any custom accommodations discussed in messages. |
| **Enable data-driven insights** | Allow queries over the historical message database for pattern analysis and operational reporting. |

---

### 3. Key Features

#### 3.1 Guesty API Integration & Message Ingestion
*   Connects directly to Guesty using the official API (API Key/Secret).
*   Utilizes webhooks for real-time, instantaneous ingestion of new guest messages.
*   Includes a fallback polling mechanism to ensure no messages are missed.
*   Parses rich message data, including guest details, reservation context, timestamps, and full text.
*   Stores parsed messages in a local database for long-term analysis and reporting.

**Functional Requirements**
*   Secure API key and secret storage (environment variables or mounted volume).
*   Webhook endpoint to receive real-time message events from Guesty.
*   Configurable polling interval for the fallback mechanism.
*   Message deduplication using the unique Guesty `messageId`.
*   Persistent local store (e.g., SQLite or JSON files).

#### 3.2 Categorization (LLM-Powered Classification)
*   Processes the text of each new message with a large language model (LLM) to classify guest intent.
*   Extracts key entities such as guest name, specific times, or requested items.
*   Assigns a category to each message for filtering and alerting.
*   **Default categories:**
    *   `EARLY_CHECKIN`
    *   `LATE_CHECKOUT`
    *   `SPECIAL_REQUEST` (e.g., extra towels, crib)
    *   `MAINTENANCE_ISSUE`
    *   `GENERAL_QUESTION`

**Functional Requirements**
*   Pluggable model support (e.g., `openai:gpt-4-turbo`, local `ollama/llama3`).
*   Prompt templates and few-shot examples stored in a configuration file.
*   Confidence score returned with each classification.
*   Cached inference results to minimize redundant API calls and costs.

#### 3.3 Notification System
*   Sends real-time alerts for high-priority message categories via configurable channels.

**Supported Channels**
*   Pushover (for instant mobile push notifications)
*   Slack or Discord (via webhook)
*   Email (for summary reports or lower-priority alerts)

**Notification Content**
*   Guest name and property
*   Category (e.g., “Late Check-out Request”)
*   Reservation dates
*   Message excerpt
*   Direct link to the conversation in the Guesty dashboard

**Functional Requirements**
*   Configurable alert triggers based on message category and confidence score.
*   Rate-limiting to prevent notification spam.
*   Notification templates (Jinja or Markdown) for easy customization.
*   Logs all sent alerts to the persistent store.

#### 3.4 Reporting Engine
*   Generates daily or ad-hoc summaries from the locally stored message and reservation data.
*   Supports natural language queries or simple filters (e.g., “today's check-ins,” “requests from last week”).
*   Consolidates multiple messages from the same conversation into a single, coherent summary.

**Example Report Output**
```
📅 Daily Summary (May 10, 2025)

- Sarah P. (Arrives today @ Sunny Cottage)
  - Early check-in requested ("we land at 10 AM")
  - 2 guests, 2 nights

- Tom R. (Arrives tomorrow @ The Loft)
  - No special requests noted.
```

**Functional Requirements**
*   Query parser supports date filters and simple keywords.
*   Aggregates messages by `reservationId` or `conversationId`.
*   Supports multiple output formats (Markdown, JSON).
*   Configurable time for scheduled daily reports (e.g., 7:00 AM local time).

#### 3.5 Historical Data Ingestion
*   A one-time or recurring script to backfill the message history from your Guesty account.
*   Enables trend analysis and provides a rich dataset for fine-tuning classification models.

**Functional Requirements**
*   Configurable lookback period (e.g., `BACKFILL_DAYS=365`).
*   Tracks ingestion progress to prevent duplicates on subsequent runs.
*   Processes historical messages through the same LLM classification pipeline.
*   Enables queries like “How many maintenance issues were reported last quarter?”

---

### 4. Architecture Overview

```
+-----------------------------+
|   Guesty API                |
|  (Webhooks & REST Endpoints)|
+--------------+--------------+
               | (Real-time events & polling)
               v
+-----------------------------+
|   Ingestion Worker          |
|  - Receives webhooks        |
|  - Parses message data      |
|  - Stores raw data in DB    |
+--------------+--------------+
               |
               v
+-----------------------------+
|   Classification Engine     |
|  - LLM categorization       |
|  - Entity extraction        |
|  - Enriches data in DB      |
+--------------+--------------+
               |
               v
+-----------------------------+
|   Local Store (SQLite)      |
|  - Raw & enriched messages  |
|  - Query cache, alert logs  |
+--------------+--------------+
               |
               v
+-----------------------------+     +-----------------------------+
|   Scheduler & Reporter      |---->|   Notification Layer        |
|  - Daily digest cron        |     |  - Pushover / Slack         |
|  - Ad-hoc query execution   |     |  - Email fallback           |
+-----------------------------+     +-----------------------------+
```
**Runtime:** Python application running in Docker
**Scheduler:** APScheduler for polling and daily reports
**Persistence:** Mounted `/data` volume for API tokens and database
**LLM Integration:** Configurable via API (OpenAI) or local models (Ollama)

---

### 5. Configuration Variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `GUESTY_API_KEY` | Your Guesty API key. | `abcdef123...` |
| `GUESTY_API_SECRET` | Your Guesty API secret. | `xyz789...` |
| `BACKFILL_DAYS` | Days of historical message ingestion. | `365` |
| `REPORT_HOUR` | Local time for the daily digest. | `07` |
| `PUSHOVER_TOKEN` | Pushover application token. | `abcdef123456` |
| `PUSHOVER_USER` | Pushover user/group key. | `u12345xyz` |
| `LLM_PROVIDER` | Model to use for classification. | `openai:gpt-4-turbo` |
| `DATA_DIR` | Persistent storage path. | `/data` |

---

### 6. User Stories

| ID | As a… | I want to… | So that… |
| :--- | :--- | :--- | :--- |
| U1 | Host | Be alerted instantly when guests request an early check-in | I can coordinate with my cleaning team immediately. |
| U2 | Host | Receive a morning summary of today’s arrivals and their requests | I know exactly what to prepare for each day without logging into Guesty. |
| U3 | Host | Search historical messages for patterns (e.g., "broken wifi") | I can identify recurring issues and improve my properties. |
| U4 | Host | Run this privately in a Docker container | My guest communication data remains secure and under my control. |

---

### 7. Success Metrics

| Metric | Target |
| :--- | :--- |
| **Classification accuracy** | ≥ 95% for key categories (e.g., check-in/out requests). |
| **Notification latency** | < 1 minute from message receipt in Guesty. |
| **Daily report generation** | Within 30 seconds. |
| **Initial setup time** | < 15 minutes. |
| **Data retention** | ≥ 2 years of searchable message history. |

---

### 8. Future Enhancements
*   **Web Dashboard:** An interactive UI for browsing messages, viewing trends, and running reports.
*   **Two-Way Communication:** Enable "quick reply" suggestions that can be sent back to Guesty with a single click.
*   **Automated Tagging:** Automatically apply tags (e.g., "needs_followup") to conversations within Guesty.
*   **Smart Home Integration:** Trigger actions (e.g., adjust thermostat for early arrival) based on classified requests.
*   **Multi-Account Support:** Monitor multiple Guesty accounts from a single InboxIntel instance.

---

### 9. Non-Goals (for MVP)
*   **Fully automated replies:** The system will suggest actions but will not message guests without user confirmation.
*   **Replacing the Guesty Inbox:** This tool is an intelligence and alerting layer, not a replacement for the Guesty UI.
*   **Managing pricing or calendar availability.**

---

### 10. Security & Privacy Considerations
*   Guesty API credentials will be stored securely using environment variables or Docker secrets, never hardcoded.
*   The local database and all application data will be stored on an encrypted volume.
*   LLM queries can be configured to redact Personally Identifiable Information (PII) before sending to external services.
*   Support for local, offline LLMs provides a maximum privacy option.

---

### 11. Timeline (MVP)

| Milestone | Description | Target |
| :--- | :--- | :--- |
| M1 | Guesty API integration (webhooks & polling) and local storage. | Week 1 |
| M2 | LLM classification engine and enrichment pipeline. | Week 2 |
| M3 | Real-time push notifications via Pushover. | Week 3 |
| M4 | Daily digest report generation. | Week 4 |
| M5 | Historical backfill script and basic query CLI. | Week 5 |

---

### 12. Appendices

**A. Example LLM Prompt Template**
```
You are a hospitality assistant that classifies guest messages from a Property Management System.
Return JSON with:
{
  "category": "EARLY_CHECKIN" | "LATE_CHECKOUT" | "SPECIAL_REQUEST" | "MAINTENANCE_ISSUE" | "GENERAL_QUESTION",
  "confidence": 0.0-1.0,
  "summary": "<one-line summary of the guest's core request>"
}
```

**B. Example Notification**
```
📬 New Guest Request: EARLY CHECK-IN
Guest: Sarah P. (@ Sunny Cottage)
Message: “Hi! Our flight lands at 10am, is there any chance we could drop our bags off early?”
Reservation: 2 nights (May 10–12)
```