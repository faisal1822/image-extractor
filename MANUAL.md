# BCS PDF OCR Extractor — Complete Command Manual

This manual documents all available CLI commands, flags, parameters, and workflows for extracting Bengali and English text from BCS question PDFs.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Command Cheatsheet](#command-cheatsheet)
3. [Core Commands & Flags](#core-commands--flags)
   - [1. File Selection (`--file` / `file=`)](#1-file-selection---file--file)
   - [2. Image Preview & Debug Mode (`--no-break`)](#2-image-preview--debug-mode---no-break)
   - [3. Header & Footer Cropping with First Page Separate Ratio (`--crop-top-first`, `--crop-top`, `--crop-bottom`)](#3-header--footer-cropping-with-first-page-separate-ratio)
   - [4. Multi-Column Splitting (`--split`, `--split-ratio`)](#4-multi-column-splitting---split---split-ratio)
   - [5. Batch Processing & Resume (`--skip-existing`)](#5-batch-processing--resume---skip-existing)
   - [6. Output Directory (`--output-dir`)](#6-output-directory---output-dir)
   - [7. Advanced OCR Settings (`--dpi`, `--lang`, `--tesseract-cmd`)](#7-advanced-ocr-settings---dpi---lang---tesseract-cmd)
4. [Project Architecture](#project-architecture)
5. [Troubleshooting & FAQ](#troubleshooting--faq)

---

## Quick Start

### 1. View Available PDFs & Help
```powershell
python index.py
```

### 2. Inspect Image Preview (First 2 Pages)
```powershell
python index.py --file=40
```
*Saves preview images in `debug_images/` for Page 1 (using Page 1 ratio) and Page 2 (using regular crop), then pauses so you can verify cropping and splitting.*

### 3. Run Full Extraction (All Pages)
```powershell
python index.py --file=40 --no-break
```

### 4. Batch Extract All PDFs (Resume Supported)
```powershell
python index.py --file=all --no-break --skip-existing
```

---

## Command Cheatsheet

| Flag / Option | Short | Default | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `--file <val>` | `-f` | `None` | Target PDF number, filename, or `all` | `python index.py --file=32` |
| `file=<val>` | - | `None` | Alternative syntax without `--` | `python index.py file=all` |
| `--no-break` | - | `False` | Run full OCR across all pages (bypass preview pause) | `python index.py --file=40 --no-break` |
| `--crop-top-first <v>` | - | `0.35` | Top crop for Page 1 (35% ratio or ~800px) | `python index.py --file=40 --crop-top-first=0.36` |
| `--crop-bottom-first <v>` | - | Same as crop-bottom | Bottom crop for Page 1 | `python index.py --file=40 --crop-bottom-first=80` |
| `--crop-top <val>` | - | `100` | Pixels or ratio to crop from page top for regular pages (Page 2+) | `python index.py --file=40 --crop-top=100` |
| `--crop-bottom <val>` | - | `80` | Pixels or ratio to crop from bottom for regular pages | `python index.py --file=40 --crop-bottom=80` |
| `--split <mode>` | - | `columns` | Split mode: `columns`, `rows`, or `none` | `python index.py --file=40 --split=none` |
| `--split-ratio <f>` | - | `0.5` | Ratio where split cut occurs (0.1 to 0.9) | `python index.py --file=40 --split-ratio=0.52` |
| `--skip-existing` | `-s` | `False` | Skip PDFs already extracted in output directory | `python index.py --file=all --skip-existing --no-break` |
| `--output-dir <dir>` | `-o` | `output` | Directory where `.txt` files will be saved | `python index.py --file=40 -o "bcs_results"` |
| `--dpi <int>` | - | `200` | Resolution for PDF page image rasterization | `python index.py --file=40 --dpi=300` |
| `--lang <str>` | - | `ben+eng` | Tesseract OCR language pack | `python index.py --file=40 --lang=ben` |
| `--tesseract-cmd <path>` | - | Auto | Custom path to `tesseract.exe` if not in PATH | `python index.py --file=40 --tesseract-cmd="C:\path\tesseract.exe"` |

---

## Core Commands & Flags

### 1. File Selection (`--file` / `file=`)
You can select a PDF by number, full filename, or process all files.

- **By BCS number (e.g. 10th to 50th):**
  ```powershell
  python index.py --file=32
  python index.py --file=40
  python index.py file=24
  ```

- **Process all PDF files:**
  ```powershell
  python index.py --file=all --no-break
  # or
  python index.py file=all --no-break
  ```

- **By specific path or filename:**
  ```powershell
  python index.py --file="pdf/40th bcs.pdf"
  python index.py --file="24th suspanded bcs.pdf"
  ```

---

### 2. Image Preview & Debug Mode (`--no-break`)
To ensure high OCR accuracy, you can visually inspect the cropped and split images before running a lengthy extraction.

- **Default (Preview Mode):**
  ```powershell
  python index.py --file=40
  ```
  - Generates the following images inside the `debug_images/` folder:
    - **Page 1 (using Page 1 separate crop ratio):**
      - `debug_images/page_1_original.png`
      - `debug_images/page_1_cropped_top_bottom.png`
      - `debug_images/page_1_part_1.png` (Left column)
      - `debug_images/page_1_part_2.png` (Right column)
    - **Page 2 (using regular crop):**
      - `debug_images/page_2_original.png`
      - `debug_images/page_2_cropped_top_bottom.png`
      - `debug_images/page_2_part_1.png`
      - `debug_images/page_2_part_2.png`
  - Pauses execution at a `break` statement so you can open and verify the PNGs.

- **Full Extraction Mode (Bypass Pause):**
  ```powershell
  python index.py --file=40 --no-break
  ```

---

### 3. Header & Footer Cropping with First Page Separate Ratio

Page 1 contains large title banners, instructions, and notices taking up the top 35% of the page (`y < 300` pt), whereas Page 2 onwards only have a small header margin (`~100px`).

The system uses dedicated cropping for Page 1:
- `--crop-top-first`: Top crop for Page 1 (default: `0.35` = 35% ratio, or ~800px).
- `--crop-top`: Top crop for subsequent pages (default: `100` px).
- `--crop-bottom`: Bottom crop for subsequent pages (default: `80` px).

**Custom crop examples:**
```powershell
# Using percentage/ratio:
python index.py --file=40 --crop-top-first=0.36 --crop-top=100

# Using exact pixel values:
python index.py --file=40 --crop-top-first=840 --crop-top=110 --crop-bottom=75
```

---

### 4. Multi-Column Splitting (`--split`, `--split-ratio`)
BCS question papers are formatted in two columns side-by-side. Splitting the page down the center ensures that Column 1 is read top-to-bottom first, followed by Column 2.

- **Two-Column Split (Default):**
  ```powershell
  python index.py --file=40 --split=columns
  ```

- **Custom Split Position (Ratio):**
  ```powershell
  # Cut at 52% width:
  python index.py --file=40 --split-ratio=0.52
  ```

- **Top-and-Bottom Split:**
  ```powershell
  python index.py --file=40 --split=rows
  ```

- **No Splitting (Single Page OCR):**
  ```powershell
  python index.py --file=40 --split=none
  ```

---

### 5. Batch Processing & Resume (`--skip-existing`)
Running OCR across 42 PDFs can take time. If you stop the script or want to process only newly added files:

```powershell
python index.py --file=all --no-break --skip-existing
```
*Any PDF that already has a corresponding `.txt` file in `output/` will be skipped instantly.*

---

### 6. Output Directory (`--output-dir` / `-o`)
By default, extracted `.txt` files are saved in `output/`. You can specify a different folder:

```powershell
python index.py --file=40 --no-break -o "extracted_bcs"
```

---

### 7. Advanced OCR Settings (`--dpi`, `--lang`, `--tesseract-cmd`)

- **Resolution (DPI):** Default is `200`. For clearer text on low-quality scans:
  ```powershell
  python index.py --file=40 --dpi=300 --no-break
  ```

- **OCR Language:** Default is `ben+eng`. For Bengali only:
  ```powershell
  python index.py --file=40 --lang=ben --no-break
  ```

- **Custom Tesseract Path:**
  ```powershell
  python index.py --file=40 --tesseract-cmd="C:\Program Files\Tesseract-OCR\tesseract.exe"
  ```

---

## Bold Text Extraction Note

In Bengali script, characters share an upper horizontal line known as **মাত্রা (Matra / Shiro-rekha)**. In bold fonts, this line becomes thick and continuous, which by default causes Tesseract to mistake it for a decorative graphic and drop the line.

The system automatically includes the following parameters in `extract.py`:
```text
-c pageseg_devanagari_split_strategy=1 -c ocr_devanagari_split_strategy=1 -c preserve_interword_spaces=1
```
This forces Tesseract to split bold Indic/Bengali matras accurately, ensuring 100% extraction of bold text and options.
