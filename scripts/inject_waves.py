#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer>=0.12.0",
#     "ruamel.yaml>=0.18.5"
# ]
# ///
"""
inject_waves.py

Purpose:
Injects 'argocd.argoproj.io/sync-wave' annotations into templated Kubernetes manifests
based on release labels defined in helmfile.
"""

import json
import os
from pathlib import Path
from typing import Dict

import typer
from ruamel.yaml import YAML

app = typer.Typer(help="Inject ArgoCD sync waves into manifests.")
yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)

def load_release_waves(manifest_dir: Path) -> Dict[str, str]:
    """Loads release metadata and extracts wave labels."""
    metadata_file = manifest_dir / "releases.json"
    if not metadata_file.exists():
        typer.secho(f"Warning: {metadata_file} not found. No waves will be injected.", fg=typer.colors.YELLOW)
        return {}

    with open(metadata_file, "r") as f:
        releases = json.load(f)

    wave_map = {}
    for rel in releases:
        name = rel.get("name")
        labels = rel.get("labels", "")
        
        # helmfile list --output json returns labels as a string "key:val,key2:val2" 
        # or sometimes as a dict depending on helmfile version.
        wave = None
        if isinstance(labels, dict):
            wave = labels.get("wave")
        elif isinstance(labels, str):
            # Parse string like "wave:-5,foo:bar"
            parts = labels.split(",")
            for p in parts:
                if p.startswith("wave:"):
                    wave = p.split(":", 1)[1]
                    break
        
        if name and wave is not None:
            wave_map[name] = str(wave)
    
    return wave_map

def inject_wave_to_file(file_path: Path, wave: str):
    """Injects the sync-wave annotation into a single YAML file."""
    try:
        # Load all documents in the file
        with open(file_path, "r") as f:
            docs = list(yaml.load_all(f))

        modified = False
        for doc in docs:
            if not doc or not isinstance(doc, dict):
                continue
            
            # Ensure metadata exists
            if "metadata" not in doc:
                doc["metadata"] = {}
            
            # Ensure annotations exists
            annotations = doc["metadata"].get("annotations")
            if annotations is None:
                annotations = {}
                doc["metadata"]["annotations"] = annotations
            
            # Inject sync-wave
            annotations["argocd.argoproj.io/sync-wave"] = wave
            
            # Map Helm hooks to ArgoCD hooks
            helm_hook = annotations.get("helm.sh/hook", "")
            if "post-install" in helm_hook or "post-upgrade" in helm_hook:
                annotations["argocd.argoproj.io/hook"] = "PostSync"
            
            if "helm.sh/hook-delete-policy" in annotations:
                del_policy = annotations["helm.sh/hook-delete-policy"]
                if "hook-succeeded" in del_policy:
                    annotations["argocd.argoproj.io/hook-delete-policy"] = "HookSucceeded"
                elif "before-hook-creation" in del_policy:
                    annotations["argocd.argoproj.io/hook-delete-policy"] = "BeforeHookCreation"
            
            modified = True

        if modified:
            with open(file_path, "w") as f:
                yaml.dump_all(docs, f)
    except Exception as e:
        typer.secho(f"Error processing {file_path}: {e}", fg=typer.colors.RED)

@app.command()
def main(
    manifest_dir: Path = typer.Argument(..., help="Directory containing the templated manifests.")
):
    if not manifest_dir.is_dir():
        typer.secho(f"Error: {manifest_dir} is not a directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    wave_map = load_release_waves(manifest_dir)
    if not wave_map:
        typer.echo("No wave labels found in releases.json. Skipping injection.")
        return

    typer.echo(f"Injecting waves based on mapping: {wave_map}")

    # Iterate through subdirectories (each corresponds to a release)
    # Helmfile templates into directories like: helmfile.yaml-<hash>-<release_name>
    for item in manifest_dir.iterdir():
        if not item.is_dir() or not item.name.startswith("helmfile.yaml-"):
            continue
        
        # Extract release name from directory name
        # Format is usually helmfile.yaml-hash-release_name
        # But wait, sometimes it's helmfile.yaml-hash-namespace-release_name 
        # Actually, let's look for the release name in the wave_map
        found_release = None
        for rel_name in wave_map.keys():
            if item.name.endswith(f"-{rel_name}"):
                found_release = rel_name
                break
        
        if not found_release:
            # Fallback: maybe it's mid-string if namespace is included
            for rel_name in wave_map.keys():
                if f"-{rel_name}/" in str(item) or f"-{rel_name}" in item.name:
                    # More careful check to avoid partial matches
                    if item.name.split("-")[-1] == rel_name:
                         found_release = rel_name
                         break

        if found_release:
            wave = wave_map[found_release]
            typer.echo(f"  -> Release '{found_release}' (wave {wave}) in {item.name}")
            
            # Process all YAML files in this directory recursively
            for yaml_file in item.rglob("*.yaml"):
                inject_wave_to_file(yaml_file, wave)

    typer.secho("✅ Sync waves injected successfully.", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
