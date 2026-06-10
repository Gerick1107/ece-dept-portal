# Cursor Prompt — Replace Gemini with Groq (LLM Insights)

---

## Context

The LLM Insights feature was previously implemented using Google Gemini 1.5/2.0 Flash. Gemini's free tier API is no longer reliably available. We are replacing it entirely with **Groq API** using the **Llama 3.3 70B** model, which is free, fast, and has a generous daily limit.

---

## Step 1 — Remove All Gemini References

Search the entire codebase for any reference to Gemini and remove or replace it:

```bash
grep -r "gemini" . --include="*.py" -l
grep -r "gemini" . --include="*.js" -l
grep -r "gemini" . --include="*.ts" -l
grep -r "GEMINI" . -l
```

For every file found:
- Remove any Gemini API URL strings (`generativelanguage.googleapis.com`)
- Remove any Gemini model name strings (`gemini-1.5-flash`, `gemini-2.0-flash`, etc.)
- Remove any Gemini-specific request body formatting (`contents`, `parts`, `generationConfig`)
- Remove any Gemini-specific response parsing (`candidates[0].content.parts[0].text`)
- Remove `GEMINI_API_KEY` references in code (the `.env` entry itself will be handled by the developer separately)

Do not remove the LLM Insights feature itself — only remove Gemini-specific implementation and replace with Groq as described below.

---

## Step 2 — Install Groq SDK

### Python backend
Add to `requirements.txt`:
```
groq>=0.9.0
```

Then run:
```bash
pip install groq
```

### If JS/Node backend
Add to `package.json` dependencies and run:
```bash
npm install groq-sdk
```

---

## Step 3 — Environment Variable

In the backend, replace all reads of `GEMINI_API_KEY` with `GROQ_API_KEY`:

**Python:**
```python
import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set in environment variables")
```

**JavaScript/Node:**
```javascript
const GROQ_API_KEY = process.env.GROQ_API_KEY;
if (!GROQ_API_KEY) throw new Error("GROQ_API_KEY not set in environment variables");
```

---

## Step 4 — Replace Gemini API Call with Groq API Call

Find the function that previously called the Gemini API (in the `POST /api/v1/llm-insights/generate` handler) and replace the entire API call block with the following:

### Python implementation:
```python
from groq import Groq

def call_llm(prompt: str) -> str:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an academic course improvement advisor for an Electronics and Communication Engineering department. Provide specific, actionable teaching and learning recommendations based on CO and PO attainment data."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        max_tokens=1024,
    )
    
    return chat_completion.choices[0].message.content
```

### JavaScript/Node implementation:
```javascript
import Groq from "groq-sdk";

async function callLLM(prompt) {
  const client = new Groq({ apiKey: process.env.GROQ_API_KEY });

  const chatCompletion = await client.chat.completions.create({
    messages: [
      {
        role: "system",
        content: "You are an academic course improvement advisor for an Electronics and Communication Engineering department. Provide specific, actionable teaching and learning recommendations based on CO and PO attainment data."
      },
      {
        role: "user",
        content: prompt
      }
    ],
    model: "llama-3.3-70b-versatile",
    temperature: 0.7,
    max_tokens: 1024,
  });

  return chatCompletion.choices[0].message.content;
}
```

---

## Step 5 — Error Handling

Replace the old Gemini error handling with Groq-specific handling:

**Python:**
```python
from groq import RateLimitError, AuthenticationError, APIError
import time

def call_llm_with_retry(prompt: str) -> str:
    for attempt in range(3):
        try:
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an academic course improvement advisor for an Electronics and Communication Engineering department. Provide specific, actionable teaching and learning recommendations based on CO and PO attainment data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1024,
            )
            return chat_completion.choices[0].message.content

        except RateLimitError:
            if attempt < 2:
                time.sleep(10)
                continue
            raise Exception("Rate limit exceeded. Please try again in a moment.")
        except AuthenticationError:
            raise Exception("Invalid GROQ_API_KEY. Please check your environment variables.")
        except APIError as e:
            raise Exception(f"Groq API error: {str(e)}")
```

**JavaScript:**
```javascript
async function callLLMWithRetry(prompt, attempts = 3) {
  const client = new Groq({ apiKey: process.env.GROQ_API_KEY });
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await client.chat.completions.create({
        messages: [
          { role: "system", content: "You are an academic course improvement advisor for an Electronics and Communication Engineering department. Provide specific, actionable teaching and learning recommendations based on CO and PO attainment data." },
          { role: "user", content: prompt }
        ],
        model: "llama-3.3-70b-versatile",
        temperature: 0.7,
        max_tokens: 1024,
      });
      return res.choices[0].message.content;
    } catch (err) {
      if (err?.status === 429 && i < attempts - 1) {
        await new Promise(r => setTimeout(r, 10000));
        continue;
      }
      if (err?.status === 401) throw new Error("Invalid GROQ_API_KEY.");
      throw new Error(`Groq API error: ${err.message}`);
    }
  }
}
```

---

## Step 6 — Prompt Template (unchanged logic, same as before)

The prompt construction logic does not change — keep all existing logic that:
- Fetches CO/PO attainment data from `copo_run_analytics_snapshots`
- Compares current semester vs previous semester
- Reads CO/PO descriptions from mapping sheets in `data/assets/`
- Formats the comparison rows with delta and DECLINED/IMPROVED labels

Only the function that sends the prompt to the LLM changes (Gemini → Groq as above).

The prompt string passed to `call_llm_with_retry()` remains exactly the same format:

```
You are an academic course improvement advisor for an engineering college (Electronics & Communication Engineering department).

Course: {course_title}
Current semester: {current_semester}
Previous semester: {previous_semester}

Course Outcome (CO) descriptions for this course:
{co_descriptions}

Programme Outcome (PO) descriptions:
{po_descriptions}

CO Attainment Comparison:
{co_rows}

PO/PSO Attainment Comparison:
{po_rows}

Based on the data above:
1. For each CO that has DECLINED compared to the previous semester, identify likely academic/pedagogical reasons specific to that CO's topic, and suggest 3-4 concrete teaching or learning strategies the faculty can adopt next semester to improve attainment for that specific CO.
2. For each CO that has IMPROVED, briefly note what may be working well and how to sustain it.
3. Based on PO/PSO attainment trends, suggest any overall course delivery improvements.
4. Keep suggestions specific to the CO topics — do not give generic advice.
5. Format your response with a clear heading for each CO, followed by a final Overall Recommendations section.
```

Single-semester fallback prompt (when no previous data exists) also remains unchanged — just pass it to `call_llm_with_retry()` instead.

---

## Step 7 — Caching (keep as-is)

The `llm_insights_cache` table and all caching logic remains exactly the same. No changes needed — just make sure the cached response is still being checked before calling `call_llm_with_retry()`, so the Groq API is not called unnecessarily on repeat views.

---

## Step 8 — VERIFY end-to-end that LLM Insights actually works

After making all the above changes, do the following verification steps and fix any errors encountered:

### 8a — Verify the route exists
```bash
# Python/FastAPI — check routes are registered
grep -r "llm-insights" . --include="*.py"

# Should show both:
# GET  /api/v1/llm-insights/comparison
# POST /api/v1/llm-insights/generate
```
If the generate route is missing, re-add it.

### 8b — Verify environment variable is loaded
Add a temporary startup log in the backend:
```python
import os
print("GROQ_API_KEY loaded:", bool(os.environ.get("GROQ_API_KEY")))
```
```javascript
console.log("GROQ_API_KEY loaded:", !!process.env.GROQ_API_KEY);
```
Restart the server and confirm it prints `True` / `true`. Remove this log after confirming.

### 8c — Test the Groq call directly
Add a standalone test function and call it once at startup (remove after confirming):

**Python:**
```python
def test_groq():
    try:
        result = call_llm_with_retry("Say: Groq is working correctly.")
        print("GROQ TEST SUCCESS:", result[:100])
    except Exception as e:
        print("GROQ TEST FAILED:", str(e))

test_groq()
```

**JavaScript:**
```javascript
callLLMWithRetry("Say: Groq is working correctly.")
  .then(r => console.log("GROQ TEST SUCCESS:", r.slice(0, 100)))
  .catch(e => console.error("GROQ TEST FAILED:", e.message));
```

Restart server — confirm `GROQ TEST SUCCESS` appears in logs. If it fails, fix the error before proceeding.

### 8d — Test the full generate endpoint
Make an actual POST request to the generate endpoint with a real course:
```bash
curl -X POST http://localhost:8000/api/v1/llm-insights/generate \
  -H "Content-Type: application/json" \
  -d '{"course_title": "ECE-230: Fields and Waves (F&W)"}'
```
Expected: JSON response with an `insights` field containing formatted text from the LLM.

If this returns an error, check backend logs for the actual exception and fix it before considering the task done.

### 8e — Test from the frontend
1. Open the LLM Insights page in the browser
2. Select a course from the dropdown
3. Confirm the AI Insights panel populates with text (not an error message)
4. Reload the page — confirm the cached response loads instantly without calling the API again
5. Select a different course — confirm a new generation is triggered

If any of steps 8a–8e fail, debug and fix before marking complete. Do not leave the feature in a broken state.

---

## Summary of what changes vs what stays the same

| Component | Action |
|---|---|
| Gemini API call | ❌ Remove entirely |
| Gemini URL / model string | ❌ Remove entirely |
| Gemini response parsing | ❌ Remove entirely |
| `GEMINI_API_KEY` references in code | ❌ Remove entirely |
| `groq` package | ✅ Add to requirements.txt / package.json |
| `call_llm_with_retry()` function | ✅ New Groq implementation |
| Prompt construction logic | ✅ Keep exactly as-is |
| Caching (`llm_insights_cache`) | ✅ Keep exactly as-is |
| Comparison data fetching | ✅ Keep exactly as-is |
| Frontend UI | ✅ Keep exactly as-is |
| Error messages shown to user | ✅ Keep exactly as-is |
