Of course. Here is a comprehensive list of tasks, broken down into logical phases, to guide a junior engineer in building the "inbox-intel" project. The tasks are designed to build upon each other, starting with the foundation and progressively adding features.

---

### **Project Task List: inbox-intel (Guesty API Edition)**

This document outlines the development tasks required to build the inbox-intel application. The project is divided into six phases, each representing a major milestone.

#### **Phase 1: Project Foundation & Setup**

*Goal: Create a stable, runnable skeleton of the application with proper configuration and logging.*

1.  **Initialize Project Structure:**
    *   Create the main project directory (`inbox-intel`).
    *   Set up subdirectories: `src` for source code, `config` for configuration files, `data` for the local database, and `tests`.
    *   Create an empty `main.py` file inside `src`.

2.  **Setup Dependency Management:**
    *   Create a `requirements.txt` file.
    *   Add initial core libraries: `requests`, `python-dotenv`, `apscheduler`, `fastapi`, `uvicorn`, `sqlalchemy`.

3.  **Implement Configuration Handling:**
    *   Create a `config.py` module in `src` to load settings from environment variables.
    *   Create a `.env.example` file listing all required variables (`GUESTY_API_KEY`, `GUESTY_API_SECRET`, `DATABASE_URL`, etc.). Users will copy this to a `.env` file.

4.  **Set Up Basic Logging:**
    *   Create a `logger.py` module that configures a standard logger to print timestamped messages to the console and/or a file.
    *   Ensure the logger can be imported and used across different modules.

5.  **Create the Database Model:**
    *   Create a `database.py` module.
    *   Using SQLAlchemy, define the database schema for a `messages` table. Include columns like `id`, `guesty_message_id` (must be unique), `conversation_id`, `reservation_id`, `guest_name`, `message_text`, `timestamp`, `is_processed`, `llm_category`, `llm_summary`, `llm_confidence`.
    *   Write a function to initialize the database and create the table if it doesn't exist.

---

#### **Phase 2: Guesty API Integration & Data Ingestion**

*Goal: Reliably fetch new guest messages from Guesty in real-time and store them in the local database.*

1.  **Build a Guesty API Client:**
    *   Create a `guesty_client.py` module.
    *   Write a function to handle authentication with the Guesty API using the key and secret from the configuration.
    *   Implement a test function to make a simple, authenticated API call (e.g., fetch a list of your properties) to verify the connection works.

2.  **Implement Webhook for Real-Time Messages:**
    *   In `main.py`, set up a basic FastAPI web server.
    *   Create a POST endpoint (e.g., `/webhooks/guesty/messages`).
    *   This endpoint should receive the JSON payload from the Guesty webhook, validate it, and log the content.
    *   Write a function in `database.py` to save a new message from the webhook payload into the `messages` table. Ensure you prevent duplicates based on `guesty_message_id`.

3.  **Implement a Polling Fallback Mechanism:**
    *   Create a `polling.py` module.
    *   Write a function that calls the Guesty API to fetch messages created in the last X minutes (e.g., 5 minutes).
    *   Use the same database function from the previous step to save any new messages found.
    *   In `main.py`, use `APScheduler` to schedule this polling function to run periodically (e.g., every 5 minutes).

---

#### **Phase 3: LLM Classification Engine**

*Goal: Process stored messages with an LLM to categorize them and extract key details.*

1.  **Create the LLM Classifier Service:**
    *   Create an `llm_classifier.py` module.
    *   Write a function `classify_message(text)` that takes message text as input.
    *   This function should construct a prompt using the template from the PRD and send it to an LLM provider (e.g., OpenAI API).
    *   It should parse the JSON response from the LLM and return the category, summary, and confidence score.

2.  **Implement Prompt Management:**
    *   Create a `prompts.yml` or `prompts.py` file to store the LLM prompt template.
    *   Modify the `classify_message` function to load its prompt from this file instead of having it hardcoded.

3.  **Create a Processing Worker:**
    *   Create a `worker.py` module.
    *   Write a function `process_unclassified_messages()`.
    *   This function should query the database for messages where `is_processed` is `False`.
    *   For each message, it should call the `llm_classifier.classify_message()` function.
    *   Upon receiving a successful classification, it must update the corresponding message record in the database with the category, summary, and confidence, and set `is_processed` to `True`.
    *   Schedule this worker function using `APScheduler` to run frequently (e.g., every 30 seconds).

---

#### **Phase 4: Real-time Notifications**

*Goal: Send instant alerts to a configured channel when an important message is classified.*

1.  **Build the Notification Service:**
    *   Create a `notifications.py` module.
    *   Implement a function `send_pushover_alert(title, message)`.
    *   This function will use the Pushover API token and user key from your configuration to send a push notification.

2.  **Integrate Notifications with the Worker:**
    *   Modify the `worker.py` from Phase 3.
    *   After a message is successfully classified, check if its category (e.g., `EARLY_CHECKIN`, `MAINTENANCE_ISSUE`) is in a configurable list of "alertable" categories.
    *   If it is, call the `send_pushover_alert` function, formatting a clear message with the guest's name, request type, and message summary.

3.  **Create Notification Templates:**
    *   Create a `templates/` directory.
    *   Store simple text or markdown templates for different notification types (e.g., `early_checkin_alert.md`).
    *   Modify the notification service to render these templates with the message data to create rich, readable alerts.

---

#### **Phase 5: Reporting Engine**

*Goal: Generate and deliver a daily summary of arrivals and special requests.*

1.  **Develop Report Generation Logic:**
    *   Create a `reporter.py` module.
    *   Write a function `generate_daily_summary()`.
    *   This function will need to:
        1.  Query the Guesty API (via `guesty_client.py`) to get all reservations arriving "today."
        2.  For each reservation, query your local database to find any associated messages that have been classified (e.g., special requests).
        3.  Format this information into a clean, readable Markdown summary, as shown in the PRD.

2.  **Schedule the Daily Report:**
    *   In `main.py`, use `APScheduler` to schedule the `generate_daily_summary()` function to run once per day at a configured time (e.g., `REPORT_HOUR=07`).

3.  **Deliver the Report:**
    *   Integrate the `reporter.py` module with the `notifications.py` module.
    *   After the summary is generated, send it as a single notification via Pushover, Slack, or Email.

---

#### **Phase 6: Finalizing and Packaging**

*Goal: Make the application easy to deploy, run, and maintain using Docker and add historical data capabilities.*

1.  **Create the Historical Backfill Script:**
    *   Create a standalone script `backfill.py`.
    *   This script should be runnable from the command line and accept a `--days` argument.
    *   It will call the Guesty API to fetch all messages from the past N days and use the existing database functions to save them.
    *   The existing worker will naturally pick up these messages and classify them over time.

2.  **Containerize the Application with Docker:**
    *   Create a `Dockerfile` in the root directory. It should define the steps to build a Python image, copy the source code, install dependencies from `requirements.txt`, and define the `CMD` to run the `main.py` application.

3.  **Create a Docker Compose File:**
    *   Create a `docker-compose.yml` file.
    *   Define a service for the `inbox-intel` application.
    *   Use the `.env` file for configuration.
    *   Define a mounted volume for the `/data` directory to ensure the SQLite database persists even if the container is restarted.

4.  **Finalize Documentation:**
    *   Create a comprehensive `README.md` file.
    *   Include:
        *   A brief overview of the project.
        *   Step-by-step instructions on how to configure the `.env` file.
        *   Simple commands for building and running the application using `docker-compose`.
        *   Instructions on how to run the `backfill.py` script.