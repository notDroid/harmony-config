#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.31.0",
#     "typer>=0.12.0",
# ]
# ///

import shutil
import tarfile
from pathlib import Path
from typing import Optional

import requests
import typer

app = typer.Typer(help="Fetch Kubernetes infrastructure definitions.")

def _copy_local_infra(local_infra_path: Path, cache_dir: Path):
    """Copies local Kubernetes infrastructure files to the cache directory."""
    typer.echo(f"Using local infra from {local_infra_path}...")
    
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        
    src_k8s_dir = local_infra_path / "k8s"
    shutil.copytree(src_k8s_dir, cache_dir)
            
    (cache_dir / ".version").write_text("local\n")

def _download_remote_infra(version: str, repo_url: str, cache_dir: Path):
    """Downloads and extracts remote Kubernetes infrastructure files to cache directory."""
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
        tar.extractall(path=extract_dir, filter='data')
        
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
    source: str = typer.Argument(..., help="The repository URL and version (e.g., https://github.com/repo.git@v1.0.0)"),
    cache_dir: Path = typer.Option(Path(".cache/k8s"), "--cache-dir", "-c", help="Directory to cache the fetched files in."),
    local_path: Optional[Path] = typer.Option(None, "--local-path", "-l", help="Local path to override fetching.")
):
    """Fetches the k8s directory from the specified source or copies it from a local path."""
    if local_path and local_path.is_dir():
        _copy_local_infra(local_path, cache_dir)
        return

    if "@" not in source:
        typer.secho("Error: Source must be in the format <repo_url>@<version>.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
        
    repo_url, version = source.rsplit("@", 1)
    if not repo_url or not version:
        typer.secho("Error: Both repository URL and version are required in the source argument.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
        
    _download_remote_infra(version, repo_url, cache_dir)

if __name__ == "__main__":
    app()
