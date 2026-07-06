"""Command-line interface for the AI CloudOps Assistant."""

import json
import click
from rich.console import Console
from rich.table import Table

from app.aws_utils import get_cloudwatch_alarms
from app.gcp_utils import get_monitoring_alerts
from app.multicloud import full_status_snapshot
from app.llm_client import LLMClient
from app.log_analyzer import analyze_log_file
from app.alerts import send_slack_alert
from app.config import settings

console = Console()


@click.group()
def cli():
    """AI CloudOps Assistant - chat with Claude about your AWS environment,
    check resource status, and analyze logs from the command line."""
    pass


@cli.command()
@click.option("--json-out", is_flag=True, help="Print raw JSON instead of a table.")
@click.option("--provider", type=click.Choice(["all", "aws", "gcp"]), default="all", help="Limit status to one provider.")
def status(json_out, provider):
    """Show a snapshot of AWS (EC2/S3/CloudWatch) and GCP (GCE/GCS/Monitoring) resources."""
    snapshot = full_status_snapshot()

    if json_out:
        console.print_json(json.dumps(snapshot))
        return

    # --- AWS ---
    if provider in ("all", "aws"):
        console.rule("[bold yellow]AWS[/bold yellow]")
        aws = snapshot["aws"]

        ec2 = aws["ec2"]
        if "error" in ec2:
            console.print(f"[red]EC2 error:[/red] {ec2['error']}")
        else:
            table = Table(title=f"EC2 Instances ({ec2['count']})")
            table.add_column("Name")
            table.add_column("ID")
            table.add_column("State")
            table.add_column("Type")
            table.add_column("AZ")
            for i in ec2["instances"]:
                state_color = "green" if i["state"] == "running" else "yellow"
                table.add_row(i["name"], i["id"], f"[{state_color}]{i['state']}[/{state_color}]", i["type"], i["az"] or "-")
            console.print(table)

        s3 = aws["s3"]
        if "error" in s3:
            console.print(f"[red]S3 error:[/red] {s3['error']}")
        else:
            console.print(f"[bold]S3 Buckets ({s3['count']}):[/bold] {', '.join(s3['buckets']) or '(none)'}")

        alarms = aws["alarms"]
        if "error" in alarms:
            console.print(f"[red]CloudWatch error:[/red] {alarms['error']}")
        else:
            console.print(f"[bold]Firing CloudWatch Alarms ({alarms['count']}):[/bold]")
            for a in alarms["alarms"]:
                console.print(f"  [red]● {a['name']}[/red] - {a['reason']}")

    # --- GCP ---
    if provider in ("all", "gcp"):
        console.print()
        console.rule("[bold blue]GCP[/bold blue]")
        gcp = snapshot["gcp"]

        if gcp.get("skipped"):
            console.print(f"[dim]GCP checks skipped: {gcp['reason']}[/dim]")
        else:
            gce = gcp["gce"]
            if "error" in gce:
                console.print(f"[red]GCE error:[/red] {gce['error']}")
            else:
                table = Table(title=f"GCE Instances ({gce['count']})")
                table.add_column("Name")
                table.add_column("Status")
                table.add_column("Machine Type")
                table.add_column("Zone")
                for i in gce["instances"]:
                    if "error" in i:
                        table.add_row(f"[red](zone error: {i['zone']})[/red]", i["error"], "-", i["zone"])
                        continue
                    status_color = "green" if i["status"] == "RUNNING" else "yellow"
                    table.add_row(i["name"], f"[{status_color}]{i['status']}[/{status_color}]", i["machine_type"], i["zone"])
                console.print(table)

            gcs = gcp["gcs"]
            if "error" in gcs:
                console.print(f"[red]GCS error:[/red] {gcs['error']}")
            else:
                console.print(f"[bold]GCS Buckets ({gcs['count']}):[/bold] {', '.join(gcs['buckets']) or '(none)'}")

            mon = gcp["monitoring"]
            if "error" in mon:
                console.print(f"[red]Cloud Monitoring error:[/red] {mon['error']}")
            else:
                console.print(f"[bold]Enabled Alert Policies ({mon['count']}):[/bold]")
                for p in mon["policies"]:
                    console.print(f"  [blue]● {p['name']}[/blue] ({p['combiner']})")


@cli.command()
@click.argument("log_file", type=click.Path(exists=True))
@click.option("--question", default=None, help="Custom question to ask about the log excerpt.")
def analyze_logs(log_file, question):
    """Extract errors from LOG_FILE and ask Claude to summarize root cause + fixes."""
    console.print(f"[cyan]Analyzing {log_file}...[/cyan]")
    result = analyze_log_file(log_file, question)
    console.print(result)


@cli.command()
def chat():
    """Start an interactive chat session with the CloudOps assistant."""
    client = LLMClient()
    history = []
    console.print("[bold cyan]AI CloudOps Assistant[/bold cyan] - type 'exit' to quit.\n")
    while True:
        try:
            message = console.input("[bold green]you>[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            break
        if message.strip().lower() in ("exit", "quit"):
            break
        try:
            reply = client.chat(message, history)
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/red]")
            break
        console.print(f"[bold magenta]assistant>[/bold magenta] {reply}\n")
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})


@cli.command()
def check_alarms():
    """Check CloudWatch (AWS) and Cloud Monitoring (GCP) alerts, and send a
    Slack alert summarizing anything firing/enabled across both."""
    message_parts = []

    alarms = get_cloudwatch_alarms()
    if "error" in alarms:
        console.print(f"[red]AWS error:[/red] {alarms['error']}")
    elif alarms["count"] == 0:
        console.print("[green]AWS: no alarms firing.[/green]")
    else:
        lines = [f"- {a['name']}: {a['reason']}" for a in alarms["alarms"]]
        part = f"🚨 AWS: {alarms['count']} CloudWatch alarm(s) firing:\n" + "\n".join(lines)
        console.print(part)
        message_parts.append(part)

    if settings.gcp_configured():
        mon = get_monitoring_alerts()
        if "error" in mon:
            console.print(f"[red]GCP error:[/red] {mon['error']}")
        elif mon["count"] == 0:
            console.print("[green]GCP: no enabled alert policies found.[/green]")
        else:
            lines = [f"- {p['name']}" for p in mon["policies"]]
            part = f"🔔 GCP: {mon['count']} enabled alert polic(ies):\n" + "\n".join(lines)
            console.print(part)
            message_parts.append(part)
    else:
        console.print("[dim]GCP checks skipped: GCP_PROJECT_ID not set.[/dim]")

    if not message_parts:
        return

    message = "\n\n".join(message_parts)
    if send_slack_alert(message):
        console.print("[green]Slack alert sent.[/green]")
    else:
        console.print("[yellow]Slack webhook not configured or send failed.[/yellow]")


@cli.command()
@click.option("--host", default=None, help="Override API host.")
@click.option("--port", default=None, type=int, help="Override API port.")
def serve(host, port):
    """Run the FastAPI server (equivalent to `uvicorn app.api:app`)."""
    import uvicorn
    from app.config import settings
    uvicorn.run(
        "app.api:app",
        host=host or settings.api_host,
        port=port or settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    cli()
