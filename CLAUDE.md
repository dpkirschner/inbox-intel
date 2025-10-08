# InboxIntel Project Context

## Project Overview
InboxIntel is a self-hosted service that connects to Guesty (property management system) via API to monitor guest messages in real-time, classify them using LLM, and send automated alerts for important requests.

## Key Features
- **Guesty API Integration**: Real-time webhook ingestion + polling fallback
- **LLM Classification**: Categorizes messages (EARLY_CHECKIN, LATE_CHECKOUT, SPECIAL_REQUEST, MAINTENANCE_ISSUE, GENERAL_QUESTION)
- **Smart Notifications**: Pushover/Slack/Email alerts for priority messages
- **Daily Reports**: Morning summaries of arrivals and special requests
- **Historical Data**: Backfill and query message history

## Architecture
- **Runtime**: Python application in Docker
- **Database**: SQLite for persistent storage
- **Scheduler**: APScheduler for polling and reports
- **LLM**: Configurable (OpenAI API or local Ollama models)

## Development Phases
1. Project Foundation & Setup
2. Guesty API Integration & Data Ingestion
3. LLM Classification Engine
4. Real-time Notifications
5. Reporting Engine
6. Finalizing and Packaging

## Key Configuration Variables
- `GUESTY_API_KEY` / `GUESTY_API_SECRET`: Guesty authentication
- `PUSHOVER_TOKEN` / `PUSHOVER_USER`: Notification credentials
- `LLM_PROVIDER`: Model selection (e.g., `openai:gpt-4-turbo`)
- `BACKFILL_DAYS`: Historical message lookback period
- `REPORT_HOUR`: Daily digest schedule time

## Project Structure
- `src/`: Source code
- `config/`: Configuration files
- `data/`: Local SQLite database
- `tests/`: Test files
- `docs/`: PRD and task plan

## Important Guidelines
- Use context7 for questions about correct syntax
- Secure credential storage (environment variables/Docker secrets)
- Message deduplication via `guesty_message_id`
- LLM responses must include category, confidence score, and summary
- All notifications include guest name, property, category, and Guesty dashboard link

## References
- Full PRD: `docs/product.md`
- Development roadmap: `docs/plan.md`
