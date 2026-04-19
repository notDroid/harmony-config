#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv>=1.2.2",
#     "requests>=2.31.0",
#     "typer>=0.12.0",
# ]
# ///
"""
fetch-k8s.py

Purpose:
This script fetches the Kubernetes infrastructure definitions. 
It operates in two modes:
1. Local Development: If LOCAL_INFRA_PATH is defined in the environment (or .env file)
   and points to a valid directory, it copies the local 'k8s' folder directly to the cache.
   This allows developers to test local changes without committing them.
2. Remote Fetch: Otherwise, it downloads a specified release archive from a GitHub repository,
   extracts the 'infra/k8s' directory, and places it in the cache.
"""

import os
import shutil
import tarfile
from pathlib import Path

import requests
import typer
from dotenv import load_dotenv

app = typer.Typer(help="Fetch Kubernetes infrastructure definitions.")


def _copy_local_infra(local_infra_path: Path, cache_dir: Path):
    """
    Copies the local Kubernetes infrastructure files to the cache directory.
    """
    typer.echo("DEBUG: Directory exists!")
    typer.echo(f"Using local infra from {local_infra_path}...")
    
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    src_k8s_dir = local_infra_path / "k8s"
    
    for item in src_k8s_dir.iterdir():
        dest = cache_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
            
    (cache_dir / ".version").write_text("local\n")


def _download_remote_infra(version: str, cache_dir: Path, repo_url: str):
    """
    Downloads and extracts the remote Kubernetes infrastructure files to the cache directory.
    """
    typer.echo("DEBUG: Directory does NOT exist.")
    
    if not version or not repo_url:
        typer.secho("Error: VERSION and REPO_URL are required if LOCAL_INFRA_PATH is not set or invalid.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
        
    typer.echo(f"Fetching k8s {version} from {repo_url}...")
    
    extract_dir = Path(".cache/temp_extract")
    temp_tar = Path(".cache/k8s.tar.gz")
    
    clean_repo_url = repo_url.rstrip("/")
    download_url = f"{clean_repo_url}/archive/refs/tags/{version}.tar.gz"
    
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    temp_tar.parent.mkdir(parents=True, exist_ok=True)
    
    typer.echo(f"Downloading from {download_url}...")
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(temp_tar, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
    
    typer.echo(f"Extracting {temp_tar} to {extract_dir}...")
    with tarfile.open(temp_tar, "r:gz") as tar:
        tar.extractall(path=extract_dir)
        
    k8s_src = None
    for path in extract_dir.rglob("*"):
        if path.is_dir() and path.parts[-2:] == ("infra", "k8s"):
            k8s_src = path
            break
            
    if not k8s_src:
        typer.secho("Error: Could not find 'infra/k8s' in the downloaded archive.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
        
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    shutil.move(str(k8s_src), str(cache_dir))
    
    shutil.rmtree(extract_dir)
    temp_tar.unlink()
    
    (cache_dir / ".version").write_text(f"{version}\n")


@app.command()
def fetch_k8s(
    version: str = typer.Argument(..., help="The version of the infrastructure to fetch."),
    cache_dir: Path = typer.Argument(..., help="The directory to cache the fetched files in."),
    repo_url: str = typer.Argument(..., help="The GitHub repository URL.")
):
    """
    Fetches the k8s directory from the specified repository or copies it from a local path.
    """
    load_dotenv()
    
    local_infra_path_str = os.environ.get("LOCAL_INFRA_PATH")
    local_infra_path = Path(local_infra_path_str) if local_infra_path_str else None
    
    typer.echo(f"DEBUG: LOCAL_INFRA_PATH is '{local_infra_path_str}', pwd is '{Path.cwd()}'")
    
    if local_infra_path and local_infra_path.is_dir():
        _copy_local_infra(local_infra_path, cache_dir)
    else:
        _download_remote_infra(version, cache_dir, repo_url)


if __name__ == "__main__":
    app()
