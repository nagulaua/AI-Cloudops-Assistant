# AI CloudOps Assistant

An AI-powered assistant (using Claude) that helps you monitor **both AWS and
GCP** resources, triage alarms/alerts, analyze log files for root causes, and
chat about your infrastructure — from the command line or a small HTTP API.

## Features

- **`status`** — combined snapshot of:
  - **AWS**: EC2 instances, S3 buckets, firing CloudWatch alarms
  - **GCP**: Compute Engine instances, Cloud Storage buckets, enabled Cloud
    Monitoring alert policies
  - Use `--provider aws` or `--provider gcp` to check just one cloud
- **`chat`** — interactive terminal chat with an SRE-flavored Claude assistant
- **`analyze-logs`** — extracts error/warning lines from a log file and asks Claude
  to summarize the likely root cause and next steps
- **`check-alarms`** — checks CloudWatch alarms *and* Cloud Monitoring alert
  policies, and optionally posts a combined summary to Slack
- **`serve`** — runs the same functionality as a FastAPI HTTP server
  (`/status`, `/chat`, `/analyze-logs`, `/alarms`, `/gcp-alerts`, `/health`)

Both clouds are **optional and independent** — the app works fine with only
AWS configured, only GCP configured, or both. Anything not configured is
skipped with a clear message rather than causing an error.

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
- AWS credentials (for AWS status/alarms) — any of the standard boto3
  credential sources work: environment variables, `~/.aws/credentials`, an
  AWS profile, or an EC2/ECS instance role.
- GCP credentials (for GCP status/alerts) — either:
  - a service account key file referenced by `GOOGLE_APPLICATION_CREDENTIALS`, or
  - Application Default Credentials via `gcloud auth application-default login`, or
  - the metadata server if running on GCE/GKE/Cloud Run
  You'll also need `GCP_PROJECT_ID` set in `.env`.

Both AWS and GCP are **optional** — chat and log analysis work with neither
configured, and `status`/`check-alarms` simply skip whichever cloud isn't set up.

## Setup

**1. Unzip the project and move into it**

```bash
unzip ai-cloudops-assistant.zip
cd ai-cloudops-assistant
```

**2. Create a virtual environment and install dependencies**

```bash
python3 -m venv venv
source venv/bin/activate          # on Windows: venv\Scripts\activate
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

Add AWS and/or GCP values too, depending on which cloud(s) you want `status` /
`check-alarms` to check:

```
# AWS - if you already have ~/.aws/credentials set up with a profile,
# just set AWS_PROFILE instead of pasting keys directly.
AWS_PROFILE=your-profile-name
AWS_REGION=us-east-1

# GCP - GCP_PROJECT_ID is what tells the assistant to check GCP at all.
GCP_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_ZONES=us-central1-a,us-east1-b
```

If you skip the AWS block, AWS checks are skipped. If you skip
`GCP_PROJECT_ID`, GCP checks are skipped. You can configure either one, both,
or neither.

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

- **`ANTHROPIC_API_KEY is not set`** — make sure you copied `.env.example` to
  `.env` and filled in a real key, and that you're running commands from the
  project root (so `.env` is found).
- **AWS `NoCredentialsError` / access denied** — either export
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, set `AWS_PROFILE` to a profile
  in `~/.aws/credentials`, or run from an environment with an attached IAM role.
  `status` and `check-alarms` will report the error clearly rather than crashing.
- **GCP checks always show "skipped"** — set `GCP_PROJECT_ID` in `.env`; that's
  the flag that turns GCP checks on.
- **GCP `DefaultCredentialsError` / permission denied** — either set
  `GOOGLE_APPLICATION_CREDENTIALS` to a service account JSON key path, or run
  `gcloud auth application-default login` first. The service account/user
  needs at least `roles/compute.viewer`, `roles/storage.objectViewer` (or
  broader), and `roles/monitoring.viewer`.
- **`ModuleNotFoundError`** — make sure your virtual environment is activated
  and `pip install -r requirements.txt` completed without errors.

## Notes

- This project makes real calls to the Anthropic API and (optionally) AWS/GCP —
  standard usage costs/rate limits for all three apply.
- Nothing here modifies your cloud resources; all AWS and GCP calls are
  read-only (`describe_*` / `list_*`).
