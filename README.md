# Books Infrastructure

## Structure

The repository is organized as follows:

- **content/**  
  Contains a folder for each volume. Inside each volume folder, chapters are stored in Markdown format.

- **devops/**  
  Contains Python scripts and YAML configuration files that define the book metadata and the processes for testing, compiling, and other automation tasks.

- **templates/**  
  Stores LibreOffice ODT templates used for styling the compiled documents.

- **resources/**  
  Contains images and widgets, with widgets provided in ODT (LibreOffice) format for integration into the final documents.

## Compiling Process ("build books")

The compiling can be performed by the build_books Github action or by the build_books.py script contained in devops.
The github action does the setup and declare the triggers, but apart from that it does the same of the script by launching the python steps contained in devops.

The process consists of several steps, implemented in python script that can be externally called as startable modules with pyhton -m or used inside a script like build_books.py, that calls them by calling a main m,ethod that takes as parameters the same parameters as command line:

1. **Content Merge**
   The `merge.py` script takes a yaml file path as parameter.
   Optionally you can pass a parameter that restricts the merge to one volume, e.g. python -m merge.py volumes.yaml -vol volume-001.
   Optionally you can pass an output --output folder that is created if does not exists and will contain the output files. The current folder is default.
   Optionally you can pass an input --input folder that contains the files. The current folder is default
   The file is like the volumes.yaml.
   The process is:
   1. read the yaml
   2. if the user passed a volume just do one volume otherwise do all volumes
   3. if the user passed an input folder you start from it otherwise from current folder and for each volume you look in the path specified as input_name in the yaml, if not specified you look in the subfolder in the input folder named after the volume (volume-001 in the example).
   4. In that folder you take all files with md extension, they are markdown files. You take them in alphabetical order and you parse each of them demoting their headers. Each headers is moved one level below, so that the H1 becomes a H2 and so on. You support both the "#" syntax of markdown and the "=" and "-" underlinings, but you output in the "#" syntax.
   Then you merge all demoted file content into one file in the folder specified by --output, or if none in the current folder.
   It is created if not exists.
   The merged file has the name specified for the volume and md extension.

2. **Entity Replacement**  
   The `entitize.py` script takes a name list file as first parameter, then a list of markdown files. It replaces the names in the form `&name;` with their unicode counterpart.
   An output folder can be provided.
   A name list (*.nam) containing the decoding of these entities.
   Example of name list:

    ```nam
    0x0020 space
    0x0021 exclamation
    0x0022 quot
    ```

3. **Custom Styles**  
   The `customize.py` script applies custom styles to the list of markdown files provided in the command line or as a parameter, using a styles .yaml like styles.yaml.
   It converts the files containing the match and replace expressions, preparing it for production.
   An output folder can be provided.
   Style are described with a style name and a list of regular expressions in the yaml file.

   For example, the *phonetic* style is applied to text that is surrounded by spaces and slashes, such as `/example/`. The regular expression to match and replace this pattern is:

   ```regex
      [\s\p{P}](/[^/]+/)[\s\p{P}]
   ```

   Such expressions are converted with the replacement expression:

   ```regex
      ‘[\1]{custom-style="Phonetic"}’
   ```

4. **Production**  
   The YAML configuration provides parameters for calling Pandoc. Pandoc is used to convert the processed Markdown content into ODT format, using the specified templates.

   In this step, referenced widgets (in the form of odt resources, like

   ```Markdown
   ![Fan Pattern](widgets/fan_pattern.odf "Fan Pattern")
   ```

   Or other format you deem better.

   ) from the Resources folder are inserted into the compiled ODT document.

   Something similar to this, according to what is specified in the volumnes.yaml:
      - name: Convert to ODT with Pandoc
        run: |
          mkdir -p build
          pandoc obj/PrAE_obj.md --reference-doc=src/templates/Egy.ott --output=build/PrAE.odt --lua-filter=src/templates/filters/odt-custom-styles.lua --verbose --embed-resources --resource-path=src
        working-directory: ${{ github.workspace }}

5. **PDF Generation**  
   Finally, Pandoc is used again to convert the ODT document into a PDF.

   Something similar to this, , according to what is specified in the volumnes.yaml
      - name: Convert ODT to PDF with LibreOffice
        run: |
          libreoffice --headless --convert-to pdf:writer_pdf_Export build/PrAE.odt --outdir build
        working-directory: ${{ github.workspace }}

## Usage

### Prerequisites

- Python 3.11 or later
- Pandoc
- LibreOffice (for PDF generation)
- PyYAML Python package

### Installation

1. Create and activate a virtual environment (optional but recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Linux
   venv\Scripts\activate    # On Windows
   ```
  
2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install Pandoc from [pandoc.org](https://pandoc.org/installing.html)

4. Install LibreOffice from [libreoffice.org](https://www.libreoffice.org/download/)

### Building Books

#### Using the Build Script

Build all volumes:

```bash
python devops/build_books.py volumes.yaml 
```

Build specific volume:

```bash
python devops/build_books.py volumes.yaml -vol volume-001
```

Build to specific output directory:

```bash
python devops/build_books.py volumes.yaml --output bin
```

Build specific volume to specific directory:

```bash
python devops/build_books.py volumes.yaml -vol volume-001 --output bin
```

### Running tests

Run the project's unit tests from the repository root. The tests expect a Python virtual environment to be activated and LibreOffice available on PATH (used for ODT -> PDF conversion).

Windows (PowerShell) using the repository `.venv`:

```powershell
# Activate the repo venv (adjust path if you named it differently)
& .\.venv\Scripts\Activate.ps1

# Ensure LibreOffice is discoverable (adjust install path if needed)
$env:Path = "C:\Program Files\LibreOffice\program;" + $env:Path

# Install dependencies if not already installed
pip install -r requirements.txt

# Run the tests (verbose)
python -m unittest -v
```

Windows (cmd.exe):

```cmd
.venv\Scripts\activate.bat
set PATH=C:\"Program Files"\LibreOffice\program;%PATH%
pip install -r requirements.txt
python -m unittest -v
```

Unix / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
export PATH="/Applications/LibreOffice.app/Contents/MacOS/:$PATH"  # macOS example
pip install -r requirements.txt
python -m unittest -v
```

Notes:

- If your virtual environment folder is named differently (for example `venv`), use that path instead of `.venv`.
- Tests write final build outputs into `tests/artdeco/temp/build` and `tests/artdeco/temp/bin` and the test suite has been configured to preserve those outputs so you can inspect them after the run.
- On CI, ensure LibreOffice is installed on the runner and available on PATH, and that the venv is activated or the runner uses the provided venv Python executable.

#### Using Individual Scripts

1. **Merge content:**

   ```bash
   python devops/merge.py devops/volumes.yaml -vol volume-001 --output obj --input content
   ```

2. **Replace entities:**

   ```bash
   python devops/entitize.py devops/entities/basic.nam obj/volume-001.md --output obj/unicode
   ```

3. **Apply custom styles:**

   ```bash
   python devops/customize.py devops/styles.yaml obj/unicode/volume-001.md --output obj/custom
   ```

4. **Build final documents:**

   ```bash
   python devops/build.py devops/volumes.yaml -vol volume-001 --input obj/custom --output build
   ```

### Configuration

- **volumes.yaml**: Main configuration for volumes and build settings
- **styles.yaml**: Custom styles and regex patterns  
- **basic.nam**: Entity definitions for Unicode character replacement

### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/build_books.yml`) that automatically builds books on:

- Push to main or develop branches
- Pull requests to main branch
- Manual trigger with optional volume selection

The workflow produces ODT and PDF artifacts that can be downloaded from the Actions page.
