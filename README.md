# AI CloudOps Assistant

An AI-powered assistant (using Claude) that helps you monitor **AWS and/or
GCP** resources, triage alarms/alerts, analyze log files for root causes, and
chat about your infrastructure — from the command line or a small HTTP API.

## Features

- **`status`** — combined snapshot of:
  - **AWS**: EC2 instances, S3 buckets, firing CloudWatch alarms
  - **GCP**: Compute Engine instances, Cloud Storage buckets, enabled Cloud
    Monitoring alert policies
  - Use `--provider aws` or `--provider gcp` to display just one cloud's results
- **`chat`** — interactive terminal chat with an SRE-flavored Claude assistant
- **`analyze-logs`** — extracts error/warning lines from a log file and asks Claude
  to summarize the likely root cause and next steps
- **`check-alarms`** — checks CloudWatch alarms and/or Cloud Monitoring alert
  policies (whichever is configured), and optionally posts a combined
  summary to Slack
- **`serve`** — runs the same functionality as a FastAPI HTTP server
  (`/status`, `/chat`, `/analyze-logs`, `/alarms`, `/gcp-alerts`, `/health`)

**At least one cloud is required** for `status` and `check-alarms` — you can
configure just AWS, just GCP, or both. If neither is configured, those two
commands return a clear error telling you what to set in `.env`. `chat` and
`analyze-logs` are unaffected either way — they only need the Anthropic key.

## Project Structure

```
ai-cloudops-assistant/
├── main.py                 # CLI entry point
├── requirements.txt
├── .env.example             # copy to .env and fill in your keys
├── app/
│   ├── config.py            # loads settings from environment/.env
│   ├── llm_client.py         # Anthropic (Claude) wrapper
│   ├── aws_utils.py          # EC2 / S3 / CloudWatch helpers (boto3)
│   ├── gcp_utils.py          # GCE / GCS / Cloud Monitoring helpers (google-cloud-*)
│   ├── multicloud.py         # combines AWS + GCP into one status snapshot
│   ├── log_analyzer.py       # log parsing + Claude analysis
│   ├── alerts.py             # optional Slack webhook alerting
│   ├── cli.py                # Click-based CLI commands
│   └── api.py                # FastAPI app
├── logs_sample/app.log       # sample log file to try analyze-logs on
└── tests/test_basic.py       # tests that run without any API keys/credentials
```

## Prerequisites

- Python 3.9+
- An Anthropic API key (for `chat` / `analyze-logs`) — get one at
  https://console.anthropic.com/
- **At least one of AWS or GCP credentials (required for `status`/`check-alarms`):**
  - **AWS** — any of the standard boto3 credential sources: environment
    variables, `~/.aws/credentials`, an AWS profile, or an EC2/ECS instance
    role (set `AWS_USE_INSTANCE_ROLE=1` in `.env` in that last case, since it
    can't be auto-detected).
  - **GCP** — either:
    - **Application Default Credentials (simplest, recommended)**: install
      the `gcloud` CLI, then run `gcloud auth application-default login` and
      `gcloud config get-value project` to find your project ID. Leave
      `GOOGLE_APPLICATION_CREDENTIALS` blank in `.env` — ADC is picked up
      automatically.
    - a service account key file referenced by `GOOGLE_APPLICATION_CREDENTIALS`, or
    - the metadata server if running on GCE/GKE/Cloud Run
    You'll also need `GCP_PROJECT_ID` set in `.env` either way.

`status` and `check-alarms` will refuse to run only if **neither** cloud is
configured. `chat` and `analyze-logs` only need the Anthropic key.

## Setup

**1. Unzip the project and move into it**

```bash
unzip ai-cloudops-assistant.zip
cd ai-cloudops-assistant
```

**2. Create a virtual environment and install dependencies**

macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (Git Bash) — note `python` instead of `python3`, and `Scripts` instead of `bin`:
```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

Windows (Command Prompt / PowerShell):
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure your environment**

```bash
cp .env.example .env
```

Then edit `.env` and fill in at least:

```
ANTHROPIC_API_KEY=sk-ant-...
```

On Windows (Git Bash), you can open it in Notepad with `notepad .env`. Make
sure there are no extra spaces around the `=` and no quotes around the value.

**For `status`/`check-alarms`, add at least one of these two blocks** (both
is fine too — leaving both out is the only thing that causes an error):

```
# AWS (add this and/or the GCP block below) - if you already have
# ~/.aws/credentials set up with a profile, just set AWS_PROFILE instead
# of pasting keys directly.
AWS_PROFILE=your-profile-name
AWS_REGION=us-east-1

# GCP (add this and/or the AWS block above)
GCP_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_ZONES=us-central1-a,us-east1-b
```

If you only fill in one block, the other cloud is simply skipped (shown as
"skipped" in `status` output) rather than causing an error — only skipping
**both** blocks causes `status`/`check-alarms` to stop with a `RuntimeError`.
`chat` and `analyze-logs` are unaffected either way.

## Running It

All commands are run through `main.py`.

**Check resource status (AWS + GCP combined)**

```bash
python main.py status
python main.py status --json-out          # raw JSON instead of tables
python main.py status --provider aws      # AWS only
python main.py status --provider gcp      # GCP only
```

**Chat with the assistant**

```bash
python main.py chat
```

Type your question, press Enter, and `exit` to quit.

**Analyze a log file** (a sample is included so you can try this immediately)

```bash
python main.py analyze-logs logs_sample/app.log
```

Or point it at your own log:

```bash
python main.py analyze-logs /var/log/myapp/error.log --question "Is this related to the deploy at 9am?"
```

**Check alarms/alerts across both clouds and notify Slack**

```bash
python main.py check-alarms
```

This checks CloudWatch alarms and (if `GCP_PROJECT_ID` is set) Cloud
Monitoring alert policies, prints both, and posts a combined summary to
Slack if `SLACK_WEBHOOK_URL` is configured.

**Run the HTTP API server**

```bash
python main.py serve
# or directly:
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

Then visit `http://localhost:8000/docs` for interactive Swagger docs, or call it directly:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/status
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Are any EC2 instances stopped right now?"}'
curl -X POST http://localhost:8000/analyze-logs \
  -F "file=@logs_sample/app.log"
curl http://localhost:8000/gcp-alerts
```

## Running Tests

The included tests don't require any API keys or cloud credentials:

```bash
pytest tests/ -v
```

## Troubleshooting

- **`ANTHROPIC_API_KEY is not set`** — copy `.env.example` to `.env`, fill in
  a real key (not the placeholder text), and run commands from the project root.
- **`anthropic.AuthenticationError: invalid x-api-key`** — the key is wrong
  or still the placeholder. Check with `grep ANTHROPIC_API_KEY .env`.
- **`anthropic.BadRequestError: credit balance is too low`** — add credits at
  https://console.anthropic.com/settings/billing.
- **AWS `NoCredentialsError` / access denied** — set `AWS_PROFILE` or
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in `.env`, or run from an
  environment with an IAM role attached.
- **`RuntimeError: This project requires at least one cloud`** — neither
  AWS nor GCP is configured in `.env`; set up at least one (see Prerequisites).
- **GCP `DefaultCredentialsError` / permission denied** — run
  `gcloud auth application-default login`, or set
  `GOOGLE_APPLICATION_CREDENTIALS` to a service account key path.
- **`ModuleNotFoundError`** — activate the venv and re-run
  `pip install -r requirements.txt`.
- **Windows: `python3` not found** — use `python` instead throughout.
