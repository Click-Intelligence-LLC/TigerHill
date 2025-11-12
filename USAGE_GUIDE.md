# TigerHill Agent Debugger - Usage Guide

**Version 0.05**

Complete guide to using TigerHill Agent Debugger for inspecting and debugging LLM interactions.

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Capturing LLM Interactions](#capturing-llm-interactions)
4. [Importing Data](#importing-data)
5. [Using the Agent Debugger](#using-the-agent-debugger)
6. [Editing Configurations](#editing-configurations)
7. [Understanding the Data Model](#understanding-the-data-model)
8. [Troubleshooting](#troubleshooting)

---

## Overview

TigerHill Agent Debugger is a tool for visualizing and editing multi-turn LLM conversations. The workflow is:

```
Capture → Import → Visualize → Edit → (Replay)
```

### Key Concepts

- **Session**: A complete conversation or interaction sequence
- **Turn**: A request-response pair within a session
- **Interaction**: Individual request or response (unified model)
- **Component**: Structured parts of a prompt (system instruction, user input, etc.)
- **Span**: Segments of a response (text, thinking, tool calls, etc.)

---

## Installation

### Prerequisites

- Node.js 18+ (for frontend)
- Python 3.8+ (for backend)
- SQLite 3.40+ (usually bundled with Python)

### Step-by-Step Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/TigerHill.git
   cd TigerHill
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   ```

3. **Install backend dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

4. **Start the backend**
   ```bash
   # From project root
   python3 -m uvicorn backend.main:app --reload
   # Backend runs at http://localhost:8000
   ```

5. **Start the frontend** (in a new terminal)
   ```bash
   npm run dev
   # Frontend runs at http://localhost:5173
   ```

6. **Open in browser**
   Navigate to `http://localhost:5173`

---

## Capturing LLM Interactions

### Using the Observer SDK

TigerHill includes an Observer SDK for non-invasive LLM interaction capture.

#### Example: Gemini CLI

```javascript
// Use the gemini_session_interceptor.cjs
const { spawn } = require('child_process');

const geminiProcess = spawn('gemini', ['chat'], {
  env: {
    ...process.env,
    NODE_OPTIONS: '--require ./tigerhill/observer/gemini_session_interceptor.cjs',
    TIGERHILL_CAPTURE_PATH: './prompt_captures/my_session',
    TIGERHILL_DEBUG: 'true'
  }
});
```

#### Example: Python with custom capture

```python
from tigerhill.observer import PromptCapture

# Initialize capture
capture = PromptCapture(
    agent_name="my-agent",
    capture_path="./captures"
)

# Your agent code...
# Captured interactions will be saved automatically
```

### Capture Output Format

Captured sessions are saved as JSON files with this structure:

```json
{
  "session_id": "uuid",
  "agent_name": "my-agent",
  "start_time": 1234567890.123,
  "end_time": 1234567899.456,
  "turns": [
    {
      "turn_number": 1,
      "request": { ... },
      "response": { ... }
    }
  ]
}
```

---

## Importing Data

### Method 1: curl (Recommended)

```bash
curl -X POST http://localhost:8000/api/import/v3/json-files \
  -F "files=@./captures/session_001.json" \
  -F "files=@./captures/session_002.json"
```

###  Method 2: Python Script

```python
from backend.services.importer_v3 import DataImporterV3
import asyncio

async def import_session():
    importer = DataImporterV3()
    result = await importer.import_single_file("./captures/session_001.json")
    print(f"Imported: {result['sessions_imported']} sessions")
    print(f"Total interactions: {result['interactions_imported']}")

asyncio.run(import_session())
```

### Method 3: Web UI (Future)

A file upload UI is planned for future versions.

### Import Result

```json
{
  "success": true,
  "imported_files": 1,
  "total_files": 1,
  "sessions_imported": 1,
  "turns_imported": 15,
  "interactions_imported": 30,
  "errors": []
}
```

---

## Using the Agent Debugger

### Session List View

When you open http://localhost:5173, you'll see:

- **Session cards** with:
  - Title (derived from agent name + timestamp)
  - Total turns
  - Total interactions
  - Primary model used
  - Start time

- Click any session to enter the debugger

### Agent Debugger Interface

The debugger has two main panels:

#### Left Panel: Turn List
- Shows all turns in the session
- Turn number (can be integers or decimals for split turns)
- Request ID (first 8 characters)
- Token count per turn
- System turns marked with ⚙️ icon

#### Right Panel: Turn Detail

**Request Section:**
- **Configuration Parameters** (editable blue panel):
  - Endpoint URL
  - Model name
  - Temperature
  - Max tokens
  - Top P
  - Top K

- **Prompt Components**:
  - System instructions
  - Conversation history
  - User input
  - Tool definitions
  - Each component shows token count

**Response Section:**
- Success/error status
- Duration (seconds)
- Token usage (input + output)
- Cost estimate
- **Response Spans**:
  - Text content
  - Thinking blocks
  - Tool calls
  - Code blocks
  - Safety ratings
  - Usage metadata

---

## Editing Configurations

### Edit Request Parameters

1. Navigate to any turn
2. Find the blue configuration panel
3. Click on any field to edit:
   - **Endpoint**: Change API URL
   - **Model**: Switch to different model
   - **Temperature**: Adjust randomness (0.0-2.0)
   - **Max Tokens**: Set output length limit
   - **Top P**: Nucleus sampling parameter (0.0-1.0)
   - **Top K**: Top-k sampling (integer or empty)

4. **Save status**: Panel shows "✓ 配置已修改" when edited

### Edit Prompt Components

1. Each component has an "编辑" (Edit) button
2. Click to enter edit mode
3. Modify text or JSON
4. Click "保存" (Save) or "取消" (Cancel)
5. Edited components are marked with blue indicator

### Replay (Mock in v0.05)

1. After editing, click "重放" (Replay) button
2. Currently returns a mock response
3. Shows:
   - Original request ID
   - Applied configuration
   - Simulated response
   - Token and cost estimates

**Note**: Actual LLM replay will be implemented in future versions.

---

## Understanding the Data Model

### V3 Unified Schema

```
sessions (one session = one conversation)
├── llm_interactions (unified requests & responses)
│   ├── type: 'request' or 'response'
│   ├── turn_number: groups related req/resp
│   ├── sequence: order within turn
│   ├── request_id: links req to resp
│   └── ...all fields...
├── prompt_components (structured request data)
│   └── linked to request interactions
└── response_spans (structured response data)
    └── linked to response interactions
```

### Turn Assignment

Turns are assigned using `request_id`:
- Each unique request_id = 1 turn
- Request and its responses share the same turn_number
- Turn numbers can be fractional (e.g., 6.1, 6.2) for split turns

### Non-LLM Interactions

System requests (like initialization) are marked:
- `metadata.is_llm_interaction = false`
- Displayed with ⚙️ icon
- Config parameters may be null

---

## Troubleshooting

### Backend won't start

**Error**: `ModuleNotFoundError`
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
```

### Frontend won't load

**Error**: `npm` command not found
```bash
# Install Node.js 18+ from nodejs.org
node --version  # Should show v18 or higher
npm install
```

### No sessions in list

**Possible causes**:
1. No data imported yet → Import JSON files
2. Wrong database file → Check `backend/database.py` DB_FILE_PATH
3. Backend not running → Verify http://localhost:8000/docs works

### Import fails

**Error**: "No session_id found in JSON"
- Check JSON structure matches expected format
- Ensure `session_id` or `conversation_id` exists at top level

**Error**: "Invalid JSON"
- Validate JSON syntax with a linter
- Check file encoding (should be UTF-8)

### Parameters show as empty

**Causes**:
1. **Non-LLM interaction** → System requests have no LLM parameters
2. **Old capture format** → Re-capture with latest Observer SDK
3. **Import issue** → Check backend logs for warnings

### Browser console errors

**Common fixes**:
```bash
# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Restart dev server
npm run dev
```

---

## FAQ

**Q: Can I edit responses?**
A: Not in v0.05. Response editing is planned for future versions.

**Q: Does replay actually call the LLM?**
A: No, v0.05 returns mock data. Real replay coming in future versions.

**Q: Can I export data?**
A: Not yet. Export functionality is planned for future releases.

**Q: What LLM providers are supported?**
A: Capture works with Gemini, OpenAI, Anthropic, and any HTTP-based LLM API.

**Q: Is my data stored securely?**
A: All data is stored locally in SQLite. No data is sent to external servers.

**Q: Can I delete sessions?**
A: Delete functionality coming in future versions. For now, delete from database manually:
```sql
DELETE FROM sessions WHERE id = 'session-id';
```

---

## Next Steps

- Explore the [database schema](./backend/database/schema_v3.sql)
- Check the [API documentation](http://localhost:8000/docs) (when backend is running)
- Review [Observer SDK code](./tigerhill/observer/) for custom integrations
- Star the project on GitHub if you find it useful!

---

**Version:** 0.05
**Last Updated:** 2025-11-12
