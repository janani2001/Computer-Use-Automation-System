# LLM Agent Discovery Loop - Architecture & Flow

## Overview

The discovery agent learns how to automate an application by:
1. Taking screenshots
2. Asking Claude "What should I do?"
3. Converting Claude's response to reusable artifacts
4. Saving for deterministic replay

---

## Architecture (4 Modular Layers)

```
┌─────────────────────────────────────────────────────────┐
│  DiscoveryAgent (agent.py)                              │
│  ├─ Orchestrates the discovery loop                    │
│  ├─ Coordinates all 3 modules below                    │
│  └─ Returns CapabilityArtifact                         │
└─────────────────────────────────────────────────────────┘
           │                │                │
           ▼                ▼                ▼
    ┌──────────────┐ ┌────────────┐ ┌─────────────┐
    │  Browser     │ │   Vision   │ │   Parser    │
    │ (browser.py) │ │(vision.py) │ │(parser.py)  │
    └──────────────┘ └────────────┘ └─────────────┘
           │                │                │
           ▼                ▼                ▼
    Playwright       Claude API      CapabilityArtifact
    • click()        • Screenshot →   • Validate schema
    • type()         • Analysis       • Convert to JSON
    • wait_for()     • JSON response  • Save to file
    • screenshot()
```

---

## 4 Modules Explained

### 1. Browser Manager (`browser.py`)

**Job**: Control Playwright browser

**Key Methods**:
- `connect(target_url)` - Launch browser and navigate
- `take_screenshot()` - Capture page as base64 PNG
- `click(selector)` - Click element by CSS selector
- `type_text(selector, text)` - Type into input
- `wait_for_element(selector)` - Wait for element to appear
- `read_element_text(selector)` - Extract text from element
- `submit_form(selector)` - Submit a form
- `disconnect()` - Close browser

**Example**:
```python
browser = BrowserManager()
await browser.connect("http://127.0.0.1:5000")
screenshot = await browser.take_screenshot()
await browser.click("#search_button")
await browser.type_text("#search_input", "M001")
await browser.submit_form("button[type='submit']")
await browser.disconnect()
```

---

### 2. Vision Client (`vision.py`)

**Job**: Communicate with Claude 3.5 Sonnet

**Key Methods**:
- `add_screenshot_to_context(screenshot_b64, message)` - Send screenshot + prompt to Claude
- `send_text_message(message)` - Send text-only message
- `extract_json_from_response(response)` - Parse JSON from Claude's response
- `reset_conversation()` - Clear chat history

**Example**:
```python
vision = VisionClient(api_key="sk-...")
response = vision.add_screenshot_to_context(
    screenshot_b64,
    "I see a banking app. Goal: look up member M001. What steps should I take?"
)
# Claude responds with detailed steps

json_data = vision.extract_json_from_response(response)
# Returns: {
#   "goal": "Look up member M001...",
#   "parameters": {...},
#   "steps": [...],
#   "outputs": {...}
# }
```

---

### 3. Response Parser (`parser.py`)

**Job**: Convert Claude's response to CapabilityArtifact (our schema)

**Key Methods**:
- `parse_discovery_response(claude_response, goal)` - Main conversion
  - Calls `_parse_parameters()` 
  - Calls `_parse_steps()`
  - Calls `_parse_outputs()`
  - Returns CapabilityArtifact
- `save_artifact(artifact)` - Save to JSON file
- `load_artifact(filepath)` - Load and validate from file

**Example**:
```python
parser = ResponseParser()

# Claude's JSON response
claude_json = {
    "goal": "Look up member M001...",
    "parameters": {"member_id": {"type": "string", "required": true}},
    "steps": [
        {"action": "click", "selector": "#search_btn", ...},
        {"action": "type", "selector": "#id_input", "value": "${member_id}", ...},
        ...
    ],
    "outputs": {"balance": {"type": "string", ...}}
}

# Convert to CapabilityArtifact
artifact = parser.parse_discovery_response(claude_json, goal)

# Save to file (artifacts/lookup_member_m001_v10.json)
path = parser.save_artifact(artifact)
```

---

### 4. Discovery Agent (`agent.py`)

**Job**: Orchestrate everything (browser + vision + parser)

**Main Method**:
```python
async def discover(target_url, goal, initial_instruction=None) -> CapabilityArtifact
```

**Flow**:
```
1. Connect browser to target_url
   └─ Uses BrowserManager.connect()

2. Take screenshot of home page
   └─ Uses BrowserManager.take_screenshot()

3. Send screenshot + goal to Claude
   └─ Uses VisionClient.add_screenshot_to_context()
   └─ Claude analyzes: "I see a search form. The goal is..."
   └─ Claude responds with JSON describing the steps

4. Parse Claude's response
   └─ Uses ResponseParser.parse_discovery_response()
   └─ Converts JSON → CapabilityArtifact
   └─ Validates with Pydantic

5. Save artifact to JSON
   └─ Uses ResponseParser.save_artifact()
   └─ File: artifacts/lookup_member_m001_v10.json

6. Disconnect browser

7. Return artifact
```

**Example Usage**:
```python
agent = DiscoveryAgent(api_key="sk-...", headless=False)

artifact = await agent.discover(
    target_url="http://127.0.0.1:5000",
    goal="Look up member M001 and read their savings balance",
    initial_instruction="Start from home page. Search for member. View details."
)

print(f"Artifact ID: {artifact.id}")
print(f"Steps: {len(artifact.steps)}")
print(f"Saved to: artifacts/{artifact.id}_v10.json")
```

---

## Data Flow (Step by Step)

```
User Input
└─ goal: "Look up member M001 and read savings balance"
└─ target_url: "http://127.0.0.1:5000"
   │
   ▼
Browser Manager
└─ Connects to Flask app
└─ Takes screenshot (PNG) → base64
   │
   ▼ (screenshot + goal)
Vision Client (Claude)
└─ Receives: "I see a banking app home page. Goal is to look up M001..."
└─ Analyzes screenshot
└─ Responds with JSON:
   {
       "goal": "Look up member...",
       "parameters": {"member_id": {...}},
       "steps": [
           {"action": "click", "selector": "#search_btn", ...},
           {"action": "type", "selector": "#id_input", "value": "${member_id}", ...},
           {"action": "wait", "selector": ".member-detail", ...},
           {"action": "read", "selector": ".savings-balance", "store_as": "balance", ...}
       ],
       "outputs": {"balance": {...}}
   }
   │
   ▼
Response Parser
└─ Validates JSON structure
└─ Converts to Python objects:
   - ParameterDefinition
   - AutomationStep
   - ElementTarget
   - OutputField
└─ Creates CapabilityArtifact
└─ Validates against Pydantic schema
   │
   ▼
Save to Disk
└─ File: artifacts/lookup_member_m001_v10.json
└─ Contains: Full artifact in JSON format
   │
   ▼
Output
└─ Returns CapabilityArtifact object
└─ Ready for deterministic replay!
```

---

## What Gets Saved (Artifact JSON)

File: `artifacts/lookup_member_m001_v10.json`

```json
{
  "version": "1.0",
  "id": "lookup_member_m001",
  "name": "Look up member M001 and read savings balance",
  "goal": "Look up member M001 and read their savings balance",
  "created_at": "2026-08-13T23:45:30",
  "parameters": {
    "member_id": {
      "type": "string",
      "description": "Member ID to look up",
      "required": true,
      "default": null
    }
  },
  "steps": [
    {
      "id": "step_1",
      "action": "click",
      "target": {
        "selector": "#member_search_btn",
        "type": "css",
        "coordinates": null,
        "accessibility_label": null,
        "description": "Search button has stable ID"
      },
      "value": null,
      "store_as": null,
      "timeout_ms": 5000,
      "description": "Click search button"
    },
    {
      "id": "step_2",
      "action": "type",
      "target": {
        "selector": "#member_id_input",
        "type": "css",
        "description": "Input field for member ID"
      },
      "value": "${member_id}",
      "store_as": null,
      "timeout_ms": 5000,
      "description": "Type member ID"
    },
    {
      "id": "step_3",
      "action": "wait",
      "target": {
        "selector": ".member-detail",
        "type": "css"
      },
      "value": null,
      "store_as": null,
      "timeout_ms": 5000,
      "description": "Wait for member detail page"
    },
    {
      "id": "step_4",
      "action": "read",
      "target": {
        "selector": ".savings-balance",
        "type": "css"
      },
      "value": null,
      "store_as": "balance",
      "timeout_ms": 5000,
      "description": "Extract savings balance"
    }
  ],
  "outputs": {
    "balance": {
      "type": "string",
      "description": "Member's savings balance"
    }
  },
  "success_condition": "Balance extracted successfully",
  "tags": ["member_lookup", "balance_inquiry"],
  "error_handlers": []
}
```

---

## Production Characteristics

✅ **Modular**: Each module has single responsibility
✅ **Testable**: Can mock each module independently
✅ **Professional**: Proper logging, error handling, type hints
✅ **Scalable**: Easy to add features (error handlers, retry logic, etc.)
✅ **Documented**: Clear docstrings and examples
✅ **Async**: Uses asyncio for non-blocking I/O

---

## Next Step: Deterministic Replay

After discovery, the saved artifact can be replayed ANY NUMBER of times:

```python
from src.replay import ReplayEngine

engine = ReplayEngine()
result = await engine.replay(
    artifact_path="artifacts/lookup_member_m001_v10.json",
    parameters={"member_id": "M002"},  # Different member!
    target_url="http://127.0.0.1:5000"
)

print(result.outputs)  # {"balance": "15400.00"}
```

Same automation, different parameters, deterministic results! 🎯
