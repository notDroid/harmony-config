#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv>=1.2.2",
#     "requests>=2.31.0",
#     "typer>=0.12.0",
# ]
# ///

import os
import shutil
import tarfile
from pathlib import Path

import requests
import typer
from dotenv import load_dotenv

app = typer.Typer(help="Fetch Kubernetes infrastructure definitions.")

def _copy_local_infra(local_infra_path: Path, cache_dir: Path):
    """Copies local Kubernetes infrastructure files to the cache directory."""
    typer.echo(f"Using local infra from {local_infra_path}...")
    
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        
    src_k8s_dir = local_infra_path / "k8s"
    shutil.copytree(src_k8s_dir, cache_dir)
            
    (cache_dir / ".version").write_text("local\n")

def _download_remote_infra(version: str, cache_dir: Path, repo_url: str):
    """Downloads and extracts remote Kubernetes infrastructure files to cache directory."""
    if not version or not repo_url:
        typer.secho("Error: VERSION and REPO_URL are required.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
        
    typer.echo(f"Fetching k8s {version} from {repo_url}...")
    
    temp_tar = Path(".cache/k8s.tar.gz")
    extract_dir = Path(".cache/temp_extract")
    
    download_url = f"{repo_url.rstrip('/')}/archive/refs/tags/{version}.tar.gz"
    
    temp_tar.parent.mkdir(parents=True, exist_ok=True)
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    
    typer.echo(f"Downloading from {download_url}...")
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(temp_tar, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
    
    typer.echo(f"Extracting to {extract_dir}...")
    with tarfile.open(temp_tar, "r:gz") as tar:
        tar.extractall(path=extract_dir)
        
    k8s_src = next((path for path in extract_dir.rglob("*") if path.is_dir() and path.parts[-2:] == ("infra", "k8s")), None)
            
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
    """Fetches the k8s directory from the specified repository or copies it from a local path."""
    load_dotenv()
    
    local_infra_path_str = os.environ.get("LOCAL_INFRA_PATH")
    local_path = Path(local_infra_path_str) if local_infra_path_str else None
    
    if local_path and local_path.is_dir():
        _copy_local_infra(local_path, cache_dir)
    else:
        _download_remote_infra(version, cache_dir, repo_url)

if __name__ == "__main__":
    app()
