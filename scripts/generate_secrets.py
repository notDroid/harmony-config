# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///

import argparse
import secrets
import string
import getpass
from pathlib import Path

def generate_password(length=24):
    """Generates a secure alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex(length=32):
    """Generates a secure hex string."""
    return secrets.token_hex(length)

def main():
    parser = argparse.ArgumentParser(description="Generate a secure secrets.yaml file.")
    parser.add_argument("env", type=str, help="The target environment (e.g., local, staging)")
    args = parser.parse_args()

    is_local = args.env.lower() == "local"
    print(f"Generating secrets for environment: {args.env}")

    if is_local:
        aws_access = "test1234"
        aws_secret = "test1234"
        s3_access = "minioadmin"
        s3_secret = "minioadmin"
    else:
        print(f"\n☁️  Please enter credentials for {args.env}:")
        aws_access = input("AWS Access Key ID: ").strip()
        aws_secret = getpass.getpass("AWS Secret Access Key: ").strip()
        
        use_same = input("Use the same credentials for S3? (y/n): ").strip().lower()
        if use_same == 'y':
            s3_access = aws_access
            s3_secret = aws_secret
        else:
            s3_access = input("S3 Access Key: ").strip()
            s3_secret = getpass.getpass("S3 Secret Key: ").strip()

    yaml_content = f"""secrets: 
  app:
    secret_key: {generate_hex(32)}
  postgres:
    password: {generate_password(24)}
  aws:
    access_key_id: {aws_access}
    secret_access_key: {aws_secret}
  s3:
    access_key: {s3_access}
    secret_key: {s3_secret}
  centrifugo:
    api_key: {generate_hex(16)}
    admin_password: {generate_password(16)}
    admin_secret: {generate_hex(16)}
"""

    out_path = Path(f"environments/{args.env}/secrets.yaml")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, "w") as f:
        f.write(yaml_content)
    
    print(f"\n✅ Generated new secure secrets at: {out_path}")

if __name__ == "__main__":
    main()