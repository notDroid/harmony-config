#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.12.0",
# ]
# ///

import secrets
import string
import getpass
import os
from pathlib import Path
from string import Template

import typer

app = typer.Typer(help="Generate a secure secrets.yaml file.")

def generate_password(length=24):
    """Generates a secure alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex(length=32):
    """Generates a secure hex string."""
    return secrets.token_hex(length)

@app.command()
def main(env: str = typer.Argument(..., help="The target environment (e.g., local, staging)")):
    is_local = env.lower() == "local"
    typer.echo(f"Generating secrets for environment: {env}")

    if is_local:
        aws_access = "test1234"
        aws_secret = "test1234"
        s3_access = "minioadmin"
        s3_secret = "minioadmin"
    else:
        typer.echo(f"\n☁️  Please enter credentials for {env}:")
        aws_access = typer.prompt("AWS Access Key ID", default="", show_default=False).strip()
        aws_secret = typer.prompt("AWS Secret Access Key", hide_input=True).strip()
        
        use_same = typer.confirm("Use the same credentials for S3?")
        if use_same:
            s3_access = aws_access
            s3_secret = aws_secret
        else:
            s3_access = typer.prompt("S3 Access Key", default="", show_default=False).strip()
            s3_secret = typer.prompt("S3 Secret Key", hide_input=True).strip()

    # Load template
    script_dir = Path(__file__).parent.resolve()
    template_path = script_dir / "templates" / "secrets.yaml.tmpl"
    
    if not template_path.exists():
        typer.secho(f"Error: Template not found at {template_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    template_content = template_path.read_text()
    
    secrets_data = {
        "secret_key": generate_hex(32),
        "postgres_password": generate_password(24),
        "aws_access_key_id": aws_access,
        "aws_secret_access_key": aws_secret,
        "s3_access_key": s3_access,
        "s3_secret_key": s3_secret,
        "centrifugo_api_key": generate_hex(16),
        "centrifugo_admin_password": generate_password(16),
        "admin_password": generate_password(16), # Compatibility with old template just in case
        "centrifugo_admin_secret": generate_hex(16),
    }

    yaml_content = Template(template_content).safe_substitute(secrets_data)

    out_path = Path(f"environments/{env}/secrets.yaml")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    out_path.write_text(yaml_content)
    
    typer.secho(f"\n✅ Generated new secure secrets at: {out_path}", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
