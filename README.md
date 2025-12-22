# Warehouse Box and Container Management Web Application

This project is a small, production-tested web application for managing warehouse boxes and shipping containers.  
It is designed so that any business with similar warehouse workflows can track inventory, build containers for outbound loads, and optionally use voice to speed up box entry.

## Core Features

- **Box management**: create, view, edit, and delete boxes with weights and detailed contents.
- **Container management**: group boxes into containers, add “custom boxes” for bulk items, and view container-level summaries.
- **Inventory overview**: see all unassigned boxes and aggregated product totals across the warehouse.
- **Reporting**: export container summaries as CSV for documentation or shipping paperwork.
- **Optional voice-powered box entry**: create simple boxes hands-free using a browser microphone and an LLM interpreter.

The application stores data in a local SQLite database by default and is intended for use on an internal network.

## Technology Stack

- Python 3
- Flask
- SQLAlchemy with SQLite
- HTML templates with Bootstrap
- Optional Gemini API integration for voice interpretation

## Installation and Setup

1. **Clone the repository** onto the machine that will host the application.

2. **Create and activate a virtual environment**:

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux / macOS
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional but recommended) Create a `.env` file** in the project root to hold environment variables:

   ```env
   GEMINI_API_KEY=your_gemini_key_here    # Optional, only needed for LLM-based voice parsing
   ```

   The application automatically reads this file if `python-dotenv` is installed (it is included in `requirements.txt`).

5. **Initialize and run the application (development)**:

   The database is created automatically on first run.

   ```bash
   python app.py
   ```

   The application will be available at `http://localhost:5000`.

## Deploying for a Small Business

For a small warehouse or recycling operation, a typical deployment is:

- A small Linux machine (for example, an Ubuntu mini PC) on the local network.
- This Flask app running behind a process manager such as `gunicorn` or `systemd`.
- Users on the same LAN access the app in their browser using the mini PC’s IP and port.

Example gunicorn command:

```bash
gunicorn -w 3 -b 0.0.0.0:5000 app:app
```

You can then point any browser on the local network to `http://server-ip:5000`.

## Using the Application

- **Boxes**: use the Boxes screen to create boxes with box numbers, weights, and line items such as laptops, PCs, LCDs (with sizes), and more.
- **Containers**: create containers, assign existing boxes, and add custom box entries for bulk items.
- **Warehouse view**: review all unassigned boxes and see product totals and LCD size breakdowns.
- **Reports**: from a container page, generate a CSV report summarizing products and quantities in that container.

### Voice Entry Workflow (Optional)

The application includes a dedicated Voice Entry page that lets operators create simple boxes using speech:

1. The browser captures speech and converts it to text.
2. The text is sent to the backend, which calls Gemini to interpret it into strict JSON (box number, weight, and contents).
3. The application shows a preview of the interpreted box.
4. The operator can click the microphone again to add more items, or confirm to save the box.

Examples of phrases the system is designed to handle:

- “Box 1221, forty five pounds, twelve laptops and fifteen twenty inch square LCDs.”
- “Add ten more laptops and five twenty four inch LCD monitors.”

Quantities for the same product and LCD size are accumulated across multiple voice entries before saving.

### Enabling Gemini for Voice Parsing

Voice entry has two modes:

- Browser-only parsing (no external services).
- Gemini-backed parsing for more complex, natural speech.

To enable Gemini:

1. Obtain an API key from Google AI Studio.
2. Set `GEMINI_API_KEY` in the environment or `.env` file on the server.

When `GEMINI_API_KEY` is missing, the `/api/voice/interpret-box` endpoint returns:

```json
{ "error": "Voice parsing unavailable" }
```

In that case, manual box entry remains fully available and the rest of the application continues to work normally.

## Database and Compatibility Notes

- The database schema is defined entirely in `app.py` via the `Box`, `BoxContent`, `Container`, and `CustomBox` models.
- Recent changes for voice entry do **not** alter the schema in any way; they only add new routes and JavaScript.
- You can safely deploy these updates against an existing production `warehouse.db` file without running migrations.

## Limitations and Assumptions

- Designed for use on a trusted internal network; there is no user authentication.
- All weights are stored and displayed in pounds.
- Voice features assume a modern browser (Chrome or Edge) with microphone access.

Any business with similar workflows can adapt this project by adjusting product types, box naming conventions, or container usage while keeping the core box/container and optional voice-entry flows intact.