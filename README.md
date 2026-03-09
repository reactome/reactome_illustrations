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

To create new XML metadata files, use the **Icon XML Metadata Generator** (see below).

## Icon XML Metadata Generator

`icon-xml-generator.html` is a self-contained HTML tool for generating icon XML metadata files. Open it in a browser — no build tools or dependencies required.

### Features

- **Category selection** — loaded from the [illustration-validator](https://github.com/reactome/illustration-validator) `categories.txt`
- **Curator search** — searches the Reactome Content Service for people by name, auto-fills ORCID
- **Designer info** — pre-filled with defaults (Cristoffer Sevilla)
- **Reference databases** — dropdown loaded from `references.txt`, with UniProt ID validation
- **Synonyms** — add/remove as needed
- **Live XML preview** — updates as you fill in the form
- **Download** — saves the XML file with the correct filename

### How to use

1. Open `icon-xml-generator.html` in a browser
2. Enter the icon identifier (e.g. `R-ICO-012345`)
3. Select a category, search for a curator, and fill in the remaining fields
4. Add references and synonyms as needed
5. Click **Download XML** to save the file
6. Move the downloaded `.xml` file into the `icons/` directory
