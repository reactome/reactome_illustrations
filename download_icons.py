#!/usr/bin/env python3
"""
Download Reactome icons from Figma and validate them.

Connects to the Figma API, finds all R-ICO- components on the "Export" page,
exports them as SVGs, saves them to the icons/ directory, and runs the
icon-validator Docker container to validate the XML metadata.

Usage:
    export FIGMA_TOKEN="your_figma_token"
    python3 download_icons.py

Environment variables:
    FIGMA_TOKEN  - Figma personal access token (required)
"""

import os
import subprocess
import sys
import shutil
import time
import requests

FIGMA_FILE_KEY = "LIsqbZHURLZuWEXVRVhniK"
EXPORT_PAGE_NAME = "Export"
ICON_PREFIX = "R-ICO-"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(SCRIPT_DIR, "icons")
REFERENCES_FILE = os.path.join(SCRIPT_DIR, "references.txt")
CATEGORIES_FILE = os.path.join(SCRIPT_DIR, "categories.txt")
VALIDATOR_IMAGE = "public.ecr.aws/reactome/icon-validator:latest"
BATCH_SIZE = 100  # Number of nodes to export per API call
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def get_figma_headers(token):
    return {"X-Figma-Token": token}


def get_file_pages(token):
    """Fetch the top-level page structure of the Figma file."""
    url = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}?depth=1"
    resp = requests.get(url, headers=get_figma_headers(token))
    resp.raise_for_status()
    return resp.json()["document"]["children"]


def find_export_page_id(pages):
    """Find the page named 'Export' and return its ID."""
    for page in pages:
        if page["name"] == EXPORT_PAGE_NAME:
            return page["id"]
    raise ValueError(f"Page '{EXPORT_PAGE_NAME}' not found. Available pages: {[p['name'] for p in pages]}")


def get_icon_nodes(token, page_id):
    """Get all R-ICO- nodes from the Export page."""
    url = f"https://api.figma.com/v1/files/{FIGMA_FILE_KEY}/nodes?ids={page_id}&depth=3"
    resp = requests.get(url, headers=get_figma_headers(token))
    resp.raise_for_status()

    page_data = resp.json()["nodes"][page_id]["document"]

    # The icons are inside a frame on the Export page
    icons = []
    for child in page_data.get("children", []):
        # Check direct children and children of frames
        if child["name"].strip().startswith(ICON_PREFIX):
            icons.append({"id": child["id"], "name": child["name"].strip()})
        for grandchild in child.get("children", []):
            if grandchild["name"].strip().startswith(ICON_PREFIX):
                icons.append({"id": grandchild["id"], "name": grandchild["name"].strip()})

    return icons


def export_svgs(token, node_ids):
    """Request SVG export URLs for a batch of node IDs."""
    ids_param = ",".join(node_ids)
    url = f"https://api.figma.com/v1/images/{FIGMA_FILE_KEY}?ids={ids_param}&format=svg"

    for attempt in range(MAX_RETRIES):
        resp = requests.get(url, headers=get_figma_headers(token))
        if resp.status_code == 429:
            wait = RETRY_DELAY * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json().get("images", {})

    raise RuntimeError(f"Failed to export SVGs after {MAX_RETRIES} retries")


def download_svg(url, filepath):
    """Download an SVG file from a URL."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(resp.text)
            return True
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"  Failed to download {filepath}: {e}")
                return False


def main():
    token = os.environ.get("FIGMA_TOKEN")
    if not token:
        print("Error: FIGMA_TOKEN environment variable is not set.")
        print("Usage: export FIGMA_TOKEN='your_token' && python3 download_icons.py")
        sys.exit(1)

    # Step 1: Find the Export page
    print("Fetching file structure...")
    pages = get_file_pages(token)
    page_id = find_export_page_id(pages)
    print(f"Found '{EXPORT_PAGE_NAME}' page (id: {page_id})")

    # Step 2: Get all R-ICO- nodes
    print("Fetching icon nodes...")
    icons = get_icon_nodes(token, page_id)
    print(f"Found {len(icons)} icons with prefix '{ICON_PREFIX}'")

    if not icons:
        print("No icons found. Exiting.")
        sys.exit(1)

    # Step 3: Clear existing SVGs (preserve XML metadata files)
    os.makedirs(ICONS_DIR, exist_ok=True)
    existing_svgs = [f for f in os.listdir(ICONS_DIR) if f.endswith(".svg")]
    if existing_svgs:
        for f in existing_svgs:
            os.remove(os.path.join(ICONS_DIR, f))
        print(f"Removed {len(existing_svgs)} existing SVGs from {ICONS_DIR}/")
    else:
        print(f"No existing SVGs to clear in {ICONS_DIR}/")

    # Step 4: Export SVGs in batches
    print(f"Exporting SVGs in batches of {BATCH_SIZE}...")
    id_to_name = {icon["id"]: icon["name"] for icon in icons}
    all_ids = list(id_to_name.keys())
    all_urls = {}

    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = all_ids[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(all_ids) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Requesting export batch {batch_num}/{total_batches} ({len(batch)} icons)...")
        urls = export_svgs(token, batch)
        all_urls.update(urls)
        # Small delay between batches to avoid rate limits
        if i + BATCH_SIZE < len(all_ids):
            time.sleep(1)

    # Step 5: Download SVGs
    print(f"Downloading {len(all_urls)} SVGs...")
    success_count = 0
    fail_count = 0

    for node_id, url in all_urls.items():
        if not url:
            name = id_to_name.get(node_id, node_id)
            print(f"  Skipping {name}: no export URL returned")
            fail_count += 1
            continue

        name = id_to_name.get(node_id, node_id)
        filename = f"{name}.svg"
        filepath = os.path.join(ICONS_DIR, filename)

        if download_svg(url, filepath):
            success_count += 1
        else:
            fail_count += 1

        # Print progress every 100 icons
        total = success_count + fail_count
        if total % 100 == 0:
            print(f"  Progress: {total}/{len(all_urls)}")

    print(f"\nDone! Downloaded {success_count} icons, {fail_count} failures.")
    print(f"Icons saved to: {ICONS_DIR}/")

    if fail_count > 0:
        print("Skipping validation due to download failures.")
        sys.exit(1)

    # Step 6: Validate icons
    validate_icons()


def validate_icons():
    """Run the icon-validator Docker container against the icons directory."""
    print("\n--- Validating icons ---")

    for f in [REFERENCES_FILE, CATEGORIES_FILE]:
        if not os.path.exists(f):
            print(f"Error: {f} not found. Cannot run validation.")
            sys.exit(1)

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{ICONS_DIR}:/data/icons",
        "-v", f"{REFERENCES_FILE}:/app/references.txt",
        "-v", f"{CATEGORIES_FILE}:/app/categories.txt",
        VALIDATOR_IMAGE,
        "java", "-jar", "./target/icon-validator-jar-with-dependencies.jar",
        "-d", "/data/icons",
        "-r", "/app/references.txt",
        "-c", "/app/categories.txt",
        "-e", "false",
    ]

    print(f"Running: {' '.join(cmd[:4])} ... icon-validator")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print validator output (it writes to stdout)
    if result.stdout:
        # Only print summary lines, not per-file progress
        for line in result.stdout.splitlines():
            if "xml files analysed" not in line:
                print(f"  {line}")
    if result.stderr:
        for line in result.stderr.splitlines():
            print(f"  {line}")

    if result.returncode != 0:
        print(f"\nValidation finished with errors (exit code {result.returncode}).")
        print("Review the errors above. The icons have still been saved.")
        sys.exit(result.returncode)
    else:
        print("Validation passed!")


if __name__ == "__main__":
    main()
