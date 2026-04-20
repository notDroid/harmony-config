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
Packages rendered Kubernetes manifests into an OCI-compliant Helm chart 
and pushes it to a container registry, so ArgoCD can natively consume it.
"""

import os
import shutil
from pathlib import Path
from string import Template

import typer
import sh

app = typer.Typer(help="Package and push rendered manifests as an OCI Helm chart.")

class ChartPackager:
    def __init__(self, manifest_dir: Path, chart_name: str, chart_version: str, registry_url: str):
        self.manifest_dir = manifest_dir
        self.chart_name = chart_name
        self.chart_version = chart_version
        self.registry_url = registry_url
        self.script_dir = Path(__file__).parent.resolve()
        self.template_dir = self.script_dir / "templates"

    def _load_template(self, name: str) -> str:
        template_file = self.template_dir / f"{name}.tmpl"
        if not template_file.exists():
            typer.secho(f"Error: Template '{name}' not found at {template_file}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        return template_file.read_text()

    def restructure_as_chart(self):
        """Restructures raw manifests into a Helm chart format."""
        typer.echo(f"Restructuring manifests in {self.manifest_dir} into a Helm chart...")
        
        templates_dir = self.manifest_dir / "templates"
        manifests_subdir = self.manifest_dir / "manifests"
        
        templates_dir.mkdir(exist_ok=True)
        manifests_subdir.mkdir(exist_ok=True)

        # Move existing manifests into the 'manifests' subdirectory
        for item in self.manifest_dir.iterdir():
            if item.name in ["templates", "manifests", "Chart.yaml", "releases.json"]:
                continue
            shutil.move(str(item), str(manifests_subdir / item.name))

        # 1. Create the all.yaml template (Go template)
        all_yaml_content = self._load_template("all.yaml")
        (templates_dir / "all.yaml").write_text(all_yaml_content)

        # 2. Create Chart.yaml using string Template
        chart_yaml_tmpl = self._load_template("Chart.yaml")
        chart_yaml_content = Template(chart_yaml_tmpl).substitute(
            chart_name=self.chart_name,
            chart_version=self.chart_version
        )
        (self.manifest_dir / "Chart.yaml").write_text(chart_yaml_content)

    def package(self, destination: str = "dist/"):
        """Runs 'helm package'."""
        typer.echo(f"Packaging {self.chart_name}:{self.chart_version}...")
        try:
            sh.helm("package", str(self.manifest_dir), "--destination", destination)
        except sh.ErrorReturnCode as e:
            typer.secho(f"Error packaging chart: {e.stderr.decode()}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

    def push(self, destination: str = "dist/"):
        """Runs 'helm push' to the OCI registry."""
        packaged_tar = Path(destination) / f"{self.chart_name}-{self.chart_version}.tgz"
        image_ref = f"oci://{self.registry_url}"
        
        typer.echo(f"Pushing {packaged_tar.name} to {image_ref}...")
        try:
            sh.helm("push", str(packaged_tar), image_ref, _fg=True)
        except sh.ErrorReturnCode as e:
            typer.secho(f"Error: helm push failed for {image_ref}", fg=typer.colors.RED)
            raise typer.Exit(code=e.exit_code)

@app.command()
def main(
    manifest_dir: Path = typer.Argument(..., help="Directory containing the manifests to package."),
    chart_name: str = typer.Argument(..., help="Name of the chart/artifact."),
    chart_version: str = typer.Argument(..., help="Version of the chart/artifact."),
    registry_url: str = typer.Argument(..., help="URL of the target OCI registry.")
):
    if not manifest_dir.is_dir():
        typer.secho(f"Error: Manifest directory '{manifest_dir}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    packager = ChartPackager(manifest_dir, chart_name, chart_version, registry_url)
    
    packager.restructure_as_chart()
    packager.package()
    packager.push()

    typer.secho(f"✅ Successfully published {chart_name}:{chart_version}", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
