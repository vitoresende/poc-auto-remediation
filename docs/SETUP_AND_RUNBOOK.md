# Step-by-Step Setup, Configuration & Execution Guide

This runbook covers every step required to set up, configure, and run each stage of the **PoC Auto-Remediation Agent (Sentry -> GitHub)** locally.

---

## Stage 0: Local Prerequisites & Repository Setup

### 1. System Requirements
- **Python:** `>= 3.10` (tested on Python `3.12`)
- **Poetry:** Dependency and virtual environment manager
- **Git:** Version control CLI

### 2. Install Project Dependencies
From the monorepo root:
```bash
cd /home/vresende/Documents/vitoresende-dev/poc-auto-remediation
poetry install
```

### 3. Verify Linter and Unit Tests
Always execute tests through Poetry:
```bash
poetry run ruff check .
poetry run pytest -v
```

### 4. Push the Monorepo to GitHub
Create a new repository on GitHub (e.g., `vitoresende/poc-auto-remediation`) and push the local `main` branch:
```bash
cd /home/vresende/Documents/vitoresende-dev/poc-auto-remediation
git branch -M main
git remote add origin git@github.com:vitoresende/poc-auto-remediation.git
git push -u origin main
```
Once pushed, GitHub Actions will automatically execute `.github/workflows/ci.yml` (`ruff check` + `pytest`).

---

## Stage 1: Running the Dummy App & Generating Error Fixtures (Package 1)

The Dummy App (`src/dummy_app`) can run in two modes:
- **Local Offline Mode (Default):** Requires zero external credentials. Uses `LocalOfflineTransport` so the Sentry SDK builds 100% authentic event payloads (with stack frames, local variables, breadcrumbs, and request headers) and writes them directly to `fixtures/sentry_<scenario>.json`.
- **Remote Sentry Cloud Mode:** When `SENTRY_DSN` is provided, sends the event to your Sentry project **and** saves the local JSON fixture in `fixtures/`.

### 1. Start the Dummy App Server
```bash
cd /home/vresende/Documents/vitoresende-dev/poc-auto-remediation
poetry run uvicorn dummy_app.main:app --reload --port 8000
```

### 2. Trigger Errors via the Interactive Web Dashboard
1. Open **`http://localhost:8000`** in your browser.
2. Click **"⚡ Trigger All Scenarios (Generate 4 Fixtures)"** in the top-right corner, or click any individual scenario button:
   - **Scenario 1 (`POST /api/scenarios/discount-bug`):** Triggers `TypeError: 'NoneType' object is not subscriptable` in `checkout_service.py` with CPF, Credit Card PAN, CVV, Email, and Bearer JWT.
   - **Scenario 2 (`POST /api/scenarios/zero-division`):** Triggers `ZeroDivisionError: float division by zero` in `checkout_service.py` with CPF, SSN, Full Card Number, and Bearer Token.
   - **Scenario 3 (`POST /api/scenarios/type-mismatch`):** Triggers `TypeError: unsupported operand type(s) for +: 'float' and 'str'` in `auth_billing_service.py` with plaintext `password`, `api_secret_key`, SSN, CPF, and JWT.
   - **Scenario 4 (`POST /api/scenarios/breadcrumb-flood`):** Triggers a 3-level call stack `AttributeError` in `auth_billing_service.py` after logging 35 noisy polling breadcrumbs + PII.
3. Inspect the captured Sentry JSON payload directly in the **Sentry Payload Inspector** panel on the page, or check the generated files in `fixtures/`:
   - `fixtures/sentry_discount_none_bug.json`
   - `fixtures/sentry_zero_division_installments.json`
   - `fixtures/sentry_type_mismatch_billing.json`
   - `fixtures/sentry_breadcrumb_flood_settlement.json`

### 3. Trigger Errors via CLI (`curl`)
You can also trigger any scenario from the terminal:
```bash
curl -X POST "http://localhost:8000/api/scenarios/discount-bug?user_email=jane.doe@enterprise.io" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature" \
  -H "X-Customer-CPF: 123.456.789-00"
```

---

## Stage 2: Connecting to Sentry Sandbox (Package 1.1)

To see the errors inside the Sentry Cloud dashboard and test real Sentry Webhooks:

### 1. Create a Sentry Project & Obtain the DSN
1. Sign in to [sentry.io](https://sentry.io/) (Free Developer plan).
2. Go to **Projects -> Create Project -> Python -> FastAPI**.
3. Copy your project's **DSN** (`https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>`).

### 2. Configure the DSN in the Dummy App
You can either:
- **Option A (Live via UI):** Paste the DSN into the top input bar at `http://localhost:8000` and click **Update DSN**.
- **Option B (Via Environment Variable on Startup):**
  ```bash
  SENTRY_DSN="https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>" \
    poetry run uvicorn dummy_app.main:app --reload --port 8000
  ```

### 3. Enable Unscrubbed PII in Sentry Project Settings (For Sandbox Testing)
By default, Sentry's cloud ingestion may scrub some fields server-side unless configured. To verify your local **Package 2 PII Sanitizer** against raw webhook payloads:
1. In Sentry, go to **Settings -> Projects -> <Your Project> -> Security & Privacy**.
2. Toggle **Data Scrubbing** off (only in this isolated test sandbox) or inspect the local `fixtures/sentry_*.json` files which capture the exact payload prior to cloud ingestion.

---

## Stage 3: Exposing Local Webhook Receiver to Sentry (For Package 5)

Since everything runs locally on your machine, when we run the **Ingestor Webhook Service** (e.g., on port `8001` or `8000`), Sentry Cloud needs a public HTTPS URL to deliver webhook events (`issue.created` / `error.created`) to your local server.

### Option A: SSH Reverse Tunnel (`localhost.run`) — Zero Installation
Run in a second terminal:
```bash
ssh -R 80:localhost:8000 nokey@localhost.run
```
Copy the generated `https://<random-id>.lhr.life` URL.

### Option B: Cloudflare Quick Tunnel (`cloudflared`) — Free & Accountless
```bash
cloudflared tunnel --url http://localhost:8000
```
Copy the generated `https://<random-name>.trycloudflare.com` URL.

### Configuring the Webhook in Sentry
1. In Sentry, navigate to **Settings -> Developer Settings -> Custom Integrations -> Create New Integration -> Internal Integration**.
2. Set **Webhook URL** to `https://<your-tunnel-url>/api/webhooks/sentry`.
3. Under **Permissions**, grant `Issue & Event: Read`.
4. Under **Webhooks**, check `issue` (`issue.created`) and `error` (`error.created`), then save.

---

## Stage 4: Configuring GitHub Credentials for Automated Pull Requests (For Package 3)

For the **GitHub Delivery Engine** to read code context, create `fix/sentry-issue-<id>` branches, and open Pull Requests:

1. Go to **GitHub -> Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens -> Generate new token**.
2. Select **Repository access -> Only select repositories** and choose `poc-auto-remediation`.
3. Under **Repository permissions**, grant:
   - **Contents:** `Read and write` (to read source context and push fix branches)
   - **Pull requests:** `Read and write` (to open automated remediation PRs)
   - **Metadata:** `Read-only`
4. Export the token in your shell session when running the agent:
   ```bash
   export GITHUB_TOKEN="github_pat_..."
   export GITHUB_REPOSITORY="vitoresende/poc-auto-remediation"
   ```
