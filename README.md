# Reactome Illustrations

SVG icons and metadata for [Reactome](https://reactome.org/) pathway diagrams, sourced from Figma.

## Contents

- `icons/` - SVG icons and XML metadata files (R-ICO-XXXXXX.svg and .xml)
- `download_icons.py` - Script to download icons from Figma and validate them
- `references.txt` - Valid reference database names for the icon validator
- `categories.txt` - Valid category names for the icon validator

## Downloading Icons from Figma

The `download_icons.py` script pulls all icons from the "Export" page of the Reactome Figma icon library, saves them as SVGs, and validates the XML metadata.

### Prerequisites

- Python 3 with `requests` (`pip install requests`)
- Docker (for the icon validator)
- A Figma personal access token

### Usage

```bash
export FIGMA_TOKEN="your_figma_token"
python3 download_icons.py
```

The script will:

1. Connect to the Figma API and find all `R-ICO-` components on the Export page
2. Export each as SVG
3. Clear the `icons/` directory and save the new SVGs (XML metadata files are preserved)
4. Run the [icon-validator](https://github.com/reactome/icon-validator) Docker container to validate the XML metadata

### XML Metadata

Each icon has a corresponding XML metadata file (`R-ICO-XXXXXX.xml`) containing categories, curator/designer info, descriptions, and database references. These files are stored alongside the SVGs in the `icons/` directory.

New XML metadata files must be created manually (or with a helper script) when new icons are added.
