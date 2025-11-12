# TigerHill Agent Debugger

**Version 0.05** - Inspect and edit LLM interaction captures with precision

A focused tool for debugging AI agents by visualizing and editing multi-turn conversations captured from LLM APIs (Gemini, OpenAI, Anthropic, etc.).

---

## 🎯 What is TigerHill Agent Debugger?

TigerHill Agent Debugger helps you:
- **Capture** LLM interactions from your agent applications
- **Import** JSON capture files into a structured database
- **Visualize** multi-turn conversations with detailed request/response breakdown
- **Edit** prompts, configurations, and replay requests with modifications

Perfect for:
- Debugging complex agent behaviors
- Optimizing prompts and configurations
- Understanding multi-turn conversation flows
- Testing prompt variations

---

## ✨ Features

### 📊 Session List
- View all imported sessions
- Quick overview: turns, interactions, model info
- One-click access to Agent Debugger

### 🔍 Agent Debugger
- **Turn-by-turn navigation** - Browse conversations chronologically
- **Request details** - View and edit prompts, parameters (model, temperature, max_tokens, top_p, top_k, endpoint)
- **Response analysis** - Inspect model outputs, token usage, duration
- **Component breakdown** - See how prompts are structured (system instructions, conversation history, user input, tools)
- **Editable configs** - Modify request parameters and prepare for replay

### 🗂️ Data Model (V3)
- **Unified interaction model** - Requests and responses as first-class citizens
- **Request ID grouping** - Automatic turn assignment without complex logic
- **Rich metadata** - Full capture of generation configs, headers, raw data
- **Component extraction** - Automatic parsing of prompt structures

---

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+** (for frontend)
- **Python 3.8+** (for backend)
- **SQLite 3.40+** (bundled with Python)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/TigerHill.git
cd TigerHill

# 2. Install frontend dependencies
npm install

# 3. Install backend dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### Running the Application

```bash
# Terminal 1: Start backend (http://localhost:8000)
python3 -m uvicorn backend.main:app --reload

# Terminal 2: Start frontend (http://localhost:5173)
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## 📖 Usage Workflow

### 1. Capture LLM Interactions

Use the TigerHill Observer SDK to capture interactions from your agent:

```python
# Example: Capture Gemini API calls
from tigerhill.observer import PromptCapture

capture = PromptCapture(
    agent_name="my-agent",
    capture_path="./captures"
)

# Your agent code here...
# Interactions are automatically saved to JSON files
```

### 2. Import Captured Data

Import JSON files into the database:

**Option A: Web UI**
- Upload files via `/api/import/v3/json-files` endpoint
- Or use a tool like `curl`:

```bash
curl -X POST http://localhost:8000/api/import/v3/json-files \
  -F "files=@./captures/session_001.json"
```

**Option B: Python script**
```python
from backend.services.importer_v3 import DataImporterV3
import asyncio

async def import_files():
    importer = DataImporterV3()
    result = await importer.import_single_file("./captures/session_001.json")
    print(result)

asyncio.run(import_files())
```

### 3. View and Debug

1. Open **http://localhost:5173**
2. See list of imported sessions
3. Click on a session to enter Agent Debugger
4. Browse turns, inspect requests/responses
5. Edit configurations and prepare replays

---

## 🗄️ Database Schema

TigerHill uses SQLite with a V3 unified schema:

- **`sessions`** - Top-level session metadata
- **`llm_interactions`** - Unified requests and responses
- **`prompt_components`** - Structured prompt breakdown
- **`response_spans`** - Response content segments

Schema file: `backend/database/schema_v3.sql`

---

## 📁 Project Structure

```
TigerHill/
├── backend/                  # FastAPI backend
│   ├── database/            # Schema and DB utilities
│   ├── routers/             # API endpoints
│   ├── services/            # Importers, parsers
│   └── main.py              # Entry point
├── src/                      # React frontend
│   ├── pages/               # SessionList, AgentDebugger
│   ├── components/          # TurnDetail, etc.
│   ├── hooks/               # useSessionV3, etc.
│   └── lib/                 # API client
├── tigerhill/               # Observer SDK (Python)
│   └── observer/            # Capture utilities
└── README.md
```

---

## 🔒 Security & Privacy

**Before sharing or publishing:**
- ✅ Remove all `.db` files (contain captured data)
- ✅ Remove all JSON captures in `prompt_captures/` or similar folders
- ✅ Remove `.env` files (may contain API keys)
- ✅ Check for hardcoded API keys, tokens, credentials
- ✅ Review `.gitignore` to exclude sensitive files

---

## 🛠️ Development

### Backend API
- FastAPI with async SQLite
- Endpoints under `/api/v3/`
- Auto-reload with `--reload` flag

### Frontend
- React 18 + TypeScript + Vite
- React Query for data fetching
- Tailwind CSS for styling

### Testing
```bash
# Backend tests
pytest

# Frontend (if tests exist)
npm test
```

---

## 📝 Roadmap

**v0.05** (Current)
- ✅ Session list and Agent Debugger
- ✅ Turn-by-turn navigation
- ✅ Editable request configurations
- ✅ V3 unified interaction model

**Future**
- 🔄 Actual replay functionality (currently mock)
- 📊 Analytics and comparison views
- 🔍 Advanced search and filtering
- 🎨 Theme customization
- 📤 Export capabilities

---

## 📄 License

Apache-2.0

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [React Query](https://tanstack.com/query)

---

## 📧 Contact

For questions, issues, or contributions, please open an issue on GitHub.

**Version:** 0.05
**Last Updated:** 2025-11-12
