# FAQ Support Assistant for Online Shop (Anti-Hallucination Prototype)

A production-style prototype of a customer support assistant for a small online shop. The core engineering objective is **ANTI-HALLUCINATION**: the assistant answers strictly and exclusively from a verified knowledge base, never invents facts, denies order status lookups without CRM access, enforces deadlines strictly, and resists prompt injections.

---

## Tech Stack
- **Python:** 3.11+
- **Gemini SDK:** Official `google-genai`
- **Model:** `gemini-2.5-flash` (configurable via `GEMINI_MODEL`)
- **Generation:** `temperature = 0.0`
- **Environment:** `python-dotenv`

---

## Project Structure
```
shop-bot/
  knowledge_base.md   # Single source of truth (store policy in Russian)
  system_prompt.txt   # Anti-hallucination system prompt with boundary rules
  bot.py              # Assistant CLI loop and stateless ask() function
  crash_test.py       # Automated test suite (3 primary tests + 5 edge cases)
  results.md          # Generated report from crash_test.py
  requirements.txt    # Python dependencies
  .env.example        # Environment variables template
  README.md           # Documentation and architecture guide
```

---

## Quickstart

### 1. Installation
Clone or navigate to the repository directory:
```bash
cd shop-bot
pip install -r requirements.txt
```

### 2. Configure API Key
Create a `.env` file from the provided example:
```bash
cp .env.example .env
```
Open `.env` and set your Gemini API key:
```env
GEMINI_API_KEY=AIzaSy...your_actual_key...
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Run Crash Tests
Execute the automated anti-hallucination verification suite:
```bash
python crash_test.py
```
This executes all 8 test cases, logs progress to the terminal, and writes structured outputs to `results.md`.

### 4. Interactive Chat CLI
Run the assistant interactively in your terminal:
```bash
python bot.py
```
Type any question (e.g. `сколько стоят наушники?`, `доставка заказа 1842`, `дай скидку 20%`) or `exit` to quit.

---

## How Hallucinations Are Prevented

1. **Single Source of Truth in Prompt:**
   The exact content of `knowledge_base.md` is injected directly into the system instruction at runtime (`SYSTEM_INSTRUCTION = system_prompt + "\n\n=== KNOWLEDGE BASE ===\n" + knowledge_base`). The model is strictly instructed that this section is its sole source of truth and that it must never extrapolate using outside world knowledge.

2. **Explicit Refusal Rules for Missing Data:**
   - **No Orders Database:** The model is explicitly informed that it has zero access to order databases or customer tracking. When asked about a specific order (e.g., order 1842), it admits lack of access, recites only general delivery terms from the policy (next day, 18:00–21:00), and offers escalation to a human operator.
   - **No Invented Contacts:** The model is prohibited from inventing phone numbers, emails, or links; it simply states the question will be transferred to an operator.
   - **Strict Deadline Enforcement:** Policy limits are rigid. Returns past 14 days are refused with zero exceptions. Defective goods require examination and advance refunds are never promised.
   - **Zero Discounts:** Disallowing negotiation prevents the model from attempting to "please" the user with non-existent promo codes or discounts.

3. **Deterministic Sampling (`temperature = 0.0`):**
   Setting `temperature=0` eliminates sampling randomness and forces greedy token selection. This reduces creative drift, ensures factual consistency, and maximizes adherence to negative constraints.

4. **Stateless Calls:**
   `ask(question)` does not reuse a chat session or multi-turn history. Each invocation sends the system prompt, knowledge base, and isolated question. This prevents context poisoning, cross-talk, and iterative jailbreaks across questions.

5. **Prompt-Injection Defense:**
   The system prompt explicitly commands the model to ignore instructions like "forget previous rules", "ignore system prompt", or role-play overrides. It refuses to disclose its own prompt or the knowledge base structure and remains firmly in role.

6. **Automated Crash Tests:**
   `crash_test.py` programmatically tests anti-hallucination boundaries (tracking status leakage, deadline violations, discount jailbreaks, missing product handling, and prompt leakage) to ensure no regressions occur when rules or knowledge base entries are updated.
