# Reactome Illustrations

SVG icons and EHLD diagrams for [Reactome](https://reactome.org/) pathway diagrams, sourced from Figma.

## Contents

- `icons/` - SVG icons and XML metadata files (R-ICO-XXXXXX.svg and .xml)
- `ehld/` - EHLD diagram SVGs (R-HSA-XXXXXX.svg)
- `download_illustrations.py` - Script to download icons and EHLDs from Figma and validate them
- `VERSION` - Current release version number

## Prerequisites

- Python 3 with `requests` (`pip install requests`)
- Docker (for the [illustration-validator](https://github.com/reactome/illustration-validator))
- A Figma personal access token

## Usage

```bash
export FIGMA_TOKEN="your_figma_token"

# Download everything (icons + EHLDs) and validate
python3 download_illustrations.py

# Icons only
python3 download_illustrations.py --icons

# EHLDs only
python3 download_illustrations.py --ehlds

# Download without validating
python3 download_illustrations.py --skip-validation
```

## What the script does

1. Connects to the Figma API and finds all components/frames on the "Export" page
2. Exports icons (`R-ICO-*`) and EHLD diagrams (`R-HSA-*`) as SVGs
3. Clears existing SVGs and saves the new ones (icon XML metadata files are preserved)
4. Runs the illustration-validator Docker container to validate:
   - **Icons**: XML metadata (categories, references, curator info)
   - **EHLDs**: SVG structure (BG, LOGO, REGION/OVERLAY groups)

## Icon XML Metadata

Each icon has a corresponding XML metadata file (`R-ICO-XXXXXX.xml`) containing categories, curator/designer info, descriptions, and database references. These are stored alongside the SVGs in the `icons/` directory.

New XML metadata files must be created manually (or with a helper script) when new icons are added.
