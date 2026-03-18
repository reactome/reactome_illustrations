# Reactome Illustrations
SVG icons and EHLD diagrams for [Reactome](https://reactome.org/) pathway diagrams, sourced from Figma.

## Contents
- `icons/` - SVG icons and XML metadata files (R-ICO-XXXXXX.svg and .xml)
- `ehld/` - EHLD diagram SVGs (R-HSA-XXXXXX.svg)
- `statics/` - SVG static diagrams (R-HSA-XXXXXX.svg)
- `download_illustrations.py` - Script to download icons and EHLDs from Figma and validate them
- `VERSION` - Current release version number
- `icon-xml-generator.html` - Use this link to access: ([icon-xml-generator](https://reactome.github.io/reactome_illustrations/icon-xml-generator))

## Prerequisites
- Python 3 with `requests` (`pip install requests`)
- Docker (for the [illustration-validator](https://github.com/reactome/illustration-validator))
- A Figma personal access token — stored as a GitHub Actions secret (`FIGMA_TOKEN`) for the GitHub Actions workflow, or set as an environment variable for local use

---

## Usage

There are two ways to download and validate illustrations: via **GitHub Actions** (recommended) or **locally** via the command line.

---

### Option 1: GitHub Actions (Recommended)

This is the preferred method. Everything runs on GitHub's servers — no local setup required beyond having write access to the repo.

#### How to trigger a download

1. Go to the **Actions** tab in the repository
2. Select **"Download illustrations from Figma"** from the left sidebar (it may be pinned at the top)
3. Click **"Run workflow"**
4. Fill in the options (see below) and click the green **"Run workflow"** button

#### Workflow options

- **What to download** — choose one of:
  - `everything` — downloads all EHLDs and all icons
  - `ehlds-only` — downloads EHLD diagrams only
  - `icons-only` — downloads icons only

- **Specific EHLDs to download** — optional. If you selected `ehlds-only` and only want to update certain diagrams, enter their IDs here space-separated (e.g. `R-HSA-1234567 R-HSA-9876543`). Leave blank to download all EHLDs.

- **Specific icons to download** — optional. If you selected `icons-only` and only want to update certain icons, enter their IDs here space-separated (e.g. `R-ICO-012345 R-ICO-012346`). Leave blank to download all icons.

> **Note:** The specific ID fields are always visible but only take effect when `ehlds-only` or `icons-only` is selected.

#### Use case 1: Full fresh download (new release)

Use this when preparing a new release and you want to pull everything fresh from Figma.

1. Make sure you are running the workflow from **main** (default)
2. Select `everything`
3. Leave both specific ID fields blank
4. Click **Run workflow**

A new branch called `figma-download-YYYY-MM-DD-HHMM` will be created automatically with all the downloaded files. Validation runs automatically after the download. Once you're happy, open a pull request from that branch to main.

#### Use case 2: Updating specific files (e.g. fixing a single EHLD or icon)

Use this when an illustrator has updated a specific file in Figma and you just want to pull that one change without re-downloading everything.

1. If a download branch already exists (e.g. `figma-download-2026-03-13-1603`), select it from the **"Use workflow from"** dropdown — this will update files directly on that branch instead of creating a new one
2. If starting fresh, leave it on **main** and a new branch will be created
3. Select `ehlds-only` or `icons-only`
4. Enter the specific ID(s) in the relevant field
5. Click **Run workflow**

Only the specified files will be updated — everything else on the branch stays untouched.

#### After the workflow runs

- If **validation passed** → open a pull request from the download branch to main. The validator will run again automatically on the PR as a final check before merging.
- If **validation failed** → the branch still exists. Fix the issue (e.g. drag a missing XML file into the `icons/` folder on GitHub), then manually re-run the **"Validate illustrations"** workflow on that branch from the Actions tab.

Once the PR is merged into main, files are automatically uploaded to S3.

---

### Option 2: Running locally

Use this if you prefer to run the download script directly on your machine.

#### Setup

```bash
pip install requests
export FIGMA_TOKEN="your_figma_token"
```

On Windows (PowerShell):
```powershell
pip install requests
$env:FIGMA_TOKEN = "your_figma_token"
```

#### Commands

```bash
# Download everything (icons + EHLDs) and validate
python3 download_illustrations.py

# Icons only
python3 download_illustrations.py --icons

# EHLDs only
python3 download_illustrations.py --ehlds

# Download without validating
python3 download_illustrations.py --skip-validation

# Download specific EHLDs only
python3 download_illustrations.py --ehlds --only R-HSA-1234567 R-HSA-9876543

# Download specific icons only
python3 download_illustrations.py --icons --only-icons R-ICO-012345 R-ICO-012346
```

After running, create a new branch, commit the changes, push, and open a pull request to main.

---

## What the script does
1. Connects to the Figma API and finds all components/frames on the "Export" page
2. Exports icons (`R-ICO-*`) and EHLD diagrams (`R-HSA-*`) as SVGs
3. Clears existing SVGs and saves the new ones (icon XML metadata files are preserved)
4. Runs the illustration-validator Docker container to validate:
   - **Icons**: XML metadata (categories, references, curator info)
   - **EHLDs**: SVG structure (BG, LOGO, REGION/OVERLAY groups)

---

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
1. Open `icon-xml-generator.html` in a browser, or use this link to access: ([icon-xml-generator](https://reactome.github.io/reactome_illustrations/icon-xml-generator))
2. Enter the icon identifier (e.g. `R-ICO-012345`)
3. Select a category, search for a curator, and fill in the remaining fields
4. Add references and synonyms as needed
5. Click **Download XML** to save the file
6. Move the downloaded `.xml` file into the `icons/` directory