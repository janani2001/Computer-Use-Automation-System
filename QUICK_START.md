# Quick Start Guide - Agent Discovery System

## Setup (First Time Only)

### 1. Create Virtual Environment
```bash
cd /Users/jananinatarajan/Desktop/interface_ai
python3 -m venv venv
```

### 2. Activate Virtual Environment
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
```bash
playwright install chromium
```

### 5. Setup Environment Variables
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

---

## Running Discovery (Every Time)

### Terminal 1: Start Mock Banking App
```bash
source venv/bin/activate
python3 target_app/app.py
```

Expected output:
```
 * Running on http://127.0.0.1:5000
```

### Terminal 2: Run Discovery Agent
```bash
cd /Users/jananinatarajan/Desktop/interface_ai
source venv/bin/activate
python3 -m src.agent.agent
```

Expected output:
```
======================================================================
STARTING DISCOVERY AGENT
======================================================================
Goal: Look up member M001 and read their savings balance
Target: http://127.0.0.1:5000

[Step 1/4] Taking initial screenshot...
[Step 2/4] Sending to Claude for analysis...
[Step 3/4] Parsing Claude's response...
[Step 4/4] Converting to CapabilityArtifact...

======================================================================
✅ DISCOVERY COMPLETE
======================================================================
Artifact ID: lookup_member_m001
Artifact saved to: artifacts/lookup_member_m001_v10.json
Steps discovered: 4
Parameters: ['member_id']
Outputs: ['balance']
```

---

## What Happens Behind the Scenes

1. **Browser connects** to http://127.0.0.1:5000
2. **Takes screenshot** of home page
3. **Sends to Claude** with goal: "Look up member M001 and read savings balance"
4. **Claude analyzes** the screenshot and responds with automation steps (JSON)
5. **Parser converts** Claude's JSON to CapabilityArtifact
6. **Saves artifact** to `artifacts/lookup_member_m001_v10.json`
7. **Returns result**

---

## Important Notes

### Cost
- Single discovery run costs ~$1-3 in Claude API calls
- This is a one-time cost per unique flow
- Replays are free (no API calls)

### API Key Required
- Set `ANTHROPIC_API_KEY` in `.env` file
- Get key from: https://console.anthropic.com

### Virtual Environment
**Always activate venv before running:**
```bash
source venv/bin/activate
```

You'll know it's active when your prompt shows `(venv) bash-3.2$`

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'playwright'"
**Solution:** Make sure venv is activated:
```bash
source venv/bin/activate
```

### "Address already in use - Port 5000 is in use"
**Solution:** Kill the process using port 5000:
```bash
lsof -ti :5000 | xargs kill -9
```

### "ANTHROPIC_API_KEY not set"
**Solution:** Set API key in `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
```

---

## Next Steps

After discovery creates an artifact:
1. **Review artifact** in `artifacts/lookup_member_m001_v10.json`
2. **Run replay** to execute the automation with different parameters
3. **Build safety layer** to add guardrails
4. **Add error handling** for resilience

---

## Files Structure

```
interface_ai/
├── venv/                    ← Virtual environment (created by venv command)
├── src/
│   ├── agent/
│   │   ├── browser.py       ← Browser control
│   │   ├── vision.py        ← Claude API client
│   │   ├── parser.py        ← Schema conversion
│   │   └── agent.py         ← Main orchestration (run this!)
│   └── artifacts/
│       └── schema.py        ← Data models
├── target_app/
│   ├── app.py               ← Flask mock banking app
│   └── templates/           ← HTML templates
├── artifacts/               ← Saved automation artifacts (output)
├── logs/                    ← Discovery logs & screenshots
├── requirements.txt         ← Python dependencies
└── .env                     ← Configuration (create from .env.example)
```

---

## Quick Test (No API Cost)

To test without calling Claude API, see [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) for module documentation and examples.
