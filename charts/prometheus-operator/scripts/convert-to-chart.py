#!/usr/bin/env python3
import os
import pathlib

import requests
from ruamel.yaml import YAML


def update_chart_yaml(version: str) -> None:
    """Update the chart.yaml file with the version of the Prometheus Operator"""

    # get the chart.yaml
    with open("Chart.yaml") as f:
        chart = YAML().load(f)

    # update the version
    chart["version"] = version
    chart["appVersion"] = version

    # write the file
    with open("Chart.yaml", "w") as f:
        YAML().dump(chart, f)


def get_bundle(version: str) -> YAML:
    """Get the bundle for a given version of the Prometheus Operator"""

    # set the URL for the bundle
    url = f"https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/{version}/bundle.yaml"

    # get the bundle
    response = requests.get(url, allow_redirects=True, timeout=5)

    # return the bundle as YAML
    return YAML().load_all(response.text)


def clean(dir: pathlib.Path) -> None:
    """Clean the directory"""
    for sub in dir.iterdir():
        if sub.is_dir():
            clean(sub)
        else:
            sub.unlink()


def main():

    # Get config values from environment
    try:
        version = os.environ.get("VERSION", "v0.60.1")
        template_dir = pathlib.Path(os.environ.get("TEMPLATE_DIR", "templates"))
        crds_dir = pathlib.Path(os.environ.get("CRDS_DIR", "crds"))

    except KeyError as e:
        raise Exception(f"Missing environment variable: {e}")

    # Get the bundle
    print(f"Getting {version} bundle...")
    bundle = get_bundle(version)

    # Clean old files
    print("Cleaning old files...")
    clean(pathlib.Path("templates"))
    clean(pathlib.Path("crds"))

    # Iterate over the docs
    print("Iterating over docs...")
    for doc in bundle:

        # skip the document if it's None
        if doc is None:
            continue

        # if the document is a CRD, set the path to the crds directory and the filename to the name of the CRD
        if doc["kind"] == "CustomResourceDefinition":
            filename = (
                pathlib.Path.cwd() / "crds" / f"{doc['metadata']['name'].lower()}.yaml"
            )
        else:
            filename = pathlib.Path.cwd() / "templates" / f"{doc['kind'].lower()}.yaml"

        # if namespace in the metadata, set the namespace to the helm release namespace
        if "namespace" in doc["metadata"]:
            doc["metadata"]["namespace"] = "{{ .Release.Namespace }}"

        # if the document is a ClusterRoleBinding, set the namespace to the helm release namespace
        if doc["kind"] == "ClusterRoleBinding":
            doc["subjects"][0]["namespace"] = "{{ .Release.Namespace }}"

        # write the file
        print(f"Writing file {filename}...")

        # Create parent directory if it doesn't exist
        if not filename.parent.exists():
            filename.parent.mkdir(parents=True)

        # Write the file
        with open(filename, "w") as f:
            YAML().dump(doc, f)

    update_chart_yaml(version)


if __name__ == "__main__":
    main()
