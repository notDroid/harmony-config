#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.12.0",
#     "sh>=2.0.6"
# ]
# ///
"""
package-oci.py

Purpose:
This script packages a set of Kubernetes manifests (or a Helm chart) into a 
gzipped tarball and pushes it as an OCI artifact to a container registry.
This is particularly useful for storing configuration artifacts or GitOps 
resources in a standard OCI registry format, which tools like Argo CD can consume.
"""

import os
import tarfile
from pathlib import Path

import typer
import sh

app = typer.Typer(help="Package and push Kubernetes manifests as an OCI artifact.")

def package_manifests(manifest_dir: Path, tar_file: Path, chart_name: str, chart_version: str):
    """
    Compresses the contents of 'manifest_dir' into a gzipped tarball.
    """
    typer.echo(f"Packaging {chart_name}:{chart_version}...")
    
    tar_file.parent.mkdir(parents=True, exist_ok=True)
    
    with tarfile.open(tar_file, "w:gz") as tar:
        for item in manifest_dir.iterdir():
            tar.add(item, arcname=item.name)

def push_to_registry(image_ref: str, tar_file: Path):
    """
    Pushes the compressed tarball to an OCI registry using the 'oras' CLI tool.
    Sets the media type required by systems like Argo CD for raw manifests.
    """
    typer.echo(f"Pushing {image_ref} to OCI registry...")
    
    media_type = "application/vnd.oci.image.layer.v1.tar+gzip"
    target = f"{tar_file}:{media_type}"
    
    try:
        sh.oras("push", image_ref, target, _fg=True)
    except sh.ErrorReturnCode as e:
        typer.secho(f"Error: oras push failed with return code {e.exit_code}.", fg=typer.colors.RED)
        raise typer.Exit(code=e.exit_code)
    except sh.CommandNotFound:
        typer.secho("Error: The 'oras' CLI tool is not installed or not found in PATH.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

@app.command()
def main(
    manifest_dir: Path = typer.Argument(..., help="Directory containing the manifests to package."),
    chart_name: str = typer.Argument(..., help="Name of the chart/artifact."),
    chart_version: str = typer.Argument(..., help="Version of the chart/artifact."),
    registry_url: str = typer.Argument(..., help="URL of the target OCI registry.")
):
    """
    Packages a directory into a tarball and pushes it to an OCI registry.
    """
    # Change current working directory to the config-repo root.
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent
    os.chdir(repo_root)
    
    tar_file = Path(f"dist/{chart_name}-{chart_version}.tar.gz")
    image_ref = f"{registry_url}/{chart_name}:{chart_version}"
    
    if not manifest_dir.is_dir():
        typer.secho(f"Error: Manifest directory '{manifest_dir}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)
        
    package_manifests(manifest_dir, tar_file, chart_name, chart_version)
    push_to_registry(image_ref, tar_file)
    
    typer.secho("✅ Successfully published OCI artifact.", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
