#!/usr/bin/env python3
"""
Download Reactome icons and EHLD diagrams from Figma and validate them.

Downloads all R-ICO- icons and R-HSA- EHLD diagrams from their respective
Figma files, saves them as SVGs, and runs the illustration-validator to validate
icon XML metadata and EHLD SVG structure.

Usage:
    export FIGMA_TOKEN="your_figma_token"
    python3 download_illustrations.py              # download and validate everything
    python3 download_illustrations.py --icons      # icons only
    python3 download_illustrations.py --ehlds      # EHLDs only
    python3 download_illustrations.py --skip-validation  # download without validating

Environment variables:
    FIGMA_TOKEN  - Figma personal access token (required)
"""

import argparse
import os
import subprocess
import sys
import time
import requests

# ── Configuration ─────────────────────────────────────────────────────────────

ICON_FILE_KEY = "LIsqbZHURLZuWEXVRVhniK"
EHLD_FILE_KEY = "B1EWm6df1eDDGwwYJKRT0x"
EXPORT_PAGE_NAME = "Export"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(SCRIPT_DIR, "icons")
EHLD_DIR = os.path.join(SCRIPT_DIR, "ehld")
REFERENCES_FILE = os.path.join(SCRIPT_DIR, "references.txt")
CATEGORIES_FILE = os.path.join(SCRIPT_DIR, "categories.txt")

VALIDATOR_IMAGE = "public.ecr.aws/reactome/illustration-validator:latest"

ICON_BATCH_SIZE = 100
EHLD_BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


# ── Figma API helpers ─────────────────────────────────────────────────────────

def figma_headers(token):
    return {"X-Figma-Token": token}


def get_export_page_id(token, file_key):
    """Find the Export page in a Figma file and return its ID."""
    url = f"https://api.figma.com/v1/files/{file_key}?depth=1"
    resp = requests.get(url, headers=figma_headers(token))
    resp.raise_for_status()
    for page in resp.json()["document"]["children"]:
        if page["name"] == EXPORT_PAGE_NAME:
            return page["id"]
    raise ValueError(f"Page '{EXPORT_PAGE_NAME}' not found in file {file_key}")


def get_nodes_on_page(token, file_key, page_id, prefix, depth=3):
    """Get all nodes whose name starts with prefix from a Figma page."""
    url = f"https://api.figma.com/v1/files/{file_key}/nodes?ids={page_id}&depth={depth}"
    resp = requests.get(url, headers=figma_headers(token))
    resp.raise_for_status()

    page_data = resp.json()["nodes"][page_id]["document"]
    nodes = []
    for child in page_data.get("children", []):
        name = child["name"].strip()
        if name.startswith(prefix):
            nodes.append({"id": child["id"], "name": name})
        for grandchild in child.get("children", []):
            gname = grandchild["name"].strip()
            if gname.startswith(prefix):
                nodes.append({"id": grandchild["id"], "name": gname})
    return nodes


def export_svgs(token, file_key, node_ids, batch_size, svg_include_id=False):
    """Request SVG export URLs from Figma in batches. Returns {node_id: url}."""
    all_urls = {}
    total_batches = (len(node_ids) + batch_size - 1) // batch_size

    for i in range(0, len(node_ids), batch_size):
        batch = node_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  Requesting export batch {batch_num}/{total_batches} ({len(batch)} items)...")

        ids_param = ",".join(batch)
        url = f"https://api.figma.com/v1/images/{file_key}?ids={ids_param}&format=svg"
        if svg_include_id:
            url += "&svg_include_id=true"

        for attempt in range(MAX_RETRIES):
            resp = requests.get(url, headers=figma_headers(token))
            if resp.status_code == 429:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            all_urls.update(resp.json().get("images", {}))
            break
        else:
            raise RuntimeError(f"Failed to export batch {batch_num} after {MAX_RETRIES} retries")

        if i + batch_size < len(node_ids):
            time.sleep(1)

    return all_urls


def download_svgs(urls, id_to_name, output_dir, label="files"):
    """Download SVG files from URLs. Returns (success_count, fail_count)."""
    print(f"Downloading {len(urls)} {label}...")
    success = fail = 0

    for node_id, url in urls.items():
        if not url:
            name = id_to_name.get(node_id, node_id)
            print(f"  Skipping {name}: no export URL returned")
            fail += 1
            continue

        name = id_to_name.get(node_id, node_id)
        filepath = os.path.join(output_dir, f"{name}.svg")

        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                success += 1
                break
            except requests.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  Failed to download {name}: {e}")
                    fail += 1

        total = success + fail
        if total % 100 == 0 and total > 0:
            print(f"  Progress: {total}/{len(urls)}")

    print(f"  Done: {success} downloaded, {fail} failures.")
    return success, fail


def clear_svgs(directory):
    """Remove all .svg files from a directory."""
    os.makedirs(directory, exist_ok=True)
    existing = [f for f in os.listdir(directory) if f.endswith(".svg")]
    for f in existing:
        os.remove(os.path.join(directory, f))
    if existing:
        print(f"  Removed {len(existing)} existing SVGs from {directory}/")


# ── Download functions ────────────────────────────────────────────────────────

def download_icons(token):
    """Download all R-ICO- icons from Figma."""
    print("\n" + "=" * 60)
    print("DOWNLOADING ICONS")
    print("=" * 60)

    page_id = get_export_page_id(token, ICON_FILE_KEY)
    print(f"Found '{EXPORT_PAGE_NAME}' page (id: {page_id})")

    nodes = get_nodes_on_page(token, ICON_FILE_KEY, page_id, "R-ICO-")
    print(f"Found {len(nodes)} icons")
    if not nodes:
        print("No icons found!")
        return False

    clear_svgs(ICONS_DIR)

    id_to_name = {n["id"]: n["name"] for n in nodes}
    urls = export_svgs(token, ICON_FILE_KEY, list(id_to_name.keys()), ICON_BATCH_SIZE)
    success, fail = download_svgs(urls, id_to_name, ICONS_DIR, "icons")

    return fail == 0


def download_ehlds(token):
    """Download all R-HSA- EHLD diagrams from Figma."""
    print("\n" + "=" * 60)
    print("DOWNLOADING EHLD DIAGRAMS")
    print("=" * 60)

    page_id = get_export_page_id(token, EHLD_FILE_KEY)
    print(f"Found '{EXPORT_PAGE_NAME}' page (id: {page_id})")

    # EHLDs are direct children of the Export page (frames, depth=1 is enough)
    url = f"https://api.figma.com/v1/files/{EHLD_FILE_KEY}/nodes?ids={page_id}&depth=1"
    resp = requests.get(url, headers=figma_headers(token))
    resp.raise_for_status()
    page_data = resp.json()["nodes"][page_id]["document"]
    nodes = [
        {"id": c["id"], "name": c["name"].strip()}
        for c in page_data.get("children", [])
        if c["name"].strip().startswith("R-HSA-")
    ]
    print(f"Found {len(nodes)} EHLD diagrams")
    if not nodes:
        print("No EHLDs found!")
        return False

    clear_svgs(EHLD_DIR)

    id_to_name = {n["id"]: n["name"] for n in nodes}
    urls = export_svgs(
        token, EHLD_FILE_KEY, list(id_to_name.keys()),
        EHLD_BATCH_SIZE, svg_include_id=True
    )
    success, fail = download_svgs(urls, id_to_name, EHLD_DIR, "EHLDs")

    return fail == 0


# ── Validation ────────────────────────────────────────────────────────────────

def validate(do_icons, do_ehlds):
    """Run the illustration-validator Docker container."""
    print("\n" + "=" * 60)
    print("VALIDATING")
    print("=" * 60)

    for f in [REFERENCES_FILE, CATEGORIES_FILE]:
        if not os.path.exists(f):
            print(f"Error: {f} not found. Cannot run validation.")
            return False

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{REFERENCES_FILE}:/app/references.txt",
        "-v", f"{CATEGORIES_FILE}:/app/categories.txt",
    ]

    validator_args = [
        "java", "-jar", "./target/illustration-validator-jar-with-dependencies.jar",
        "-r", "/app/references.txt",
        "-c", "/app/categories.txt",
        "-e", "false",
    ]

    if do_icons:
        cmd += ["-v", f"{ICONS_DIR}:/data/icons"]
        validator_args += ["-d", "/data/icons"]
    else:
        # Validator requires -d, point to a mounted empty-ish path
        cmd += ["-v", f"{EHLD_DIR}:/data/icons"]
        validator_args += ["-d", "/data/icons"]

    if do_ehlds:
        cmd += ["-v", f"{EHLD_DIR}:/data/ehld"]
        validator_args += ["-s", "/data/ehld"]

    cmd += [VALIDATOR_IMAGE] + validator_args

    print("Running illustration-validator...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Print relevant output (skip per-file progress noise)
    for line in (result.stdout + result.stderr).splitlines():
        if "xml files analysed" in line:
            continue
        if "EHLD files validated" in line and "218 / 218" not in line:
            continue
        line = line.strip()
        if line:
            print(f"  {line}")

    if result.returncode != 0:
        print("\nValidation finished with errors. Review the output above.")
    else:
        print("\nValidation passed!")

    return result.returncode == 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download Reactome icons and EHLD diagrams from Figma and validate them."
    )
    parser.add_argument("--icons", action="store_true", help="Download icons only")
    parser.add_argument("--ehlds", action="store_true", help="Download EHLDs only")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation step")
    args = parser.parse_args()

    # If neither flag is set, do both
    do_icons = args.icons or not (args.icons or args.ehlds)
    do_ehlds = args.ehlds or not (args.icons or args.ehlds)

    token = os.environ.get("FIGMA_TOKEN")
    if not token:
        print("Error: FIGMA_TOKEN environment variable is not set.")
        print("Usage: export FIGMA_TOKEN='your_token' && python3 download_illustrations.py")
        sys.exit(1)

    if do_icons:
        if not download_icons(token):
            print("\nIcon download had failures. Exiting.")
            sys.exit(1)

    if do_ehlds:
        if not download_ehlds(token):
            print("\nEHLD download had failures. Exiting.")
            sys.exit(1)

    if args.skip_validation:
        print("\nSkipping validation (--skip-validation).")
        sys.exit(0)

    if not validate(do_icons, do_ehlds):
        sys.exit(1)


if __name__ == "__main__":
    main()
