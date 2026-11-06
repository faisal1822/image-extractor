import os
import io
import sys
import shutil

# Try to import required libraries with user-friendly error messages
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None


# Default Tesseract configuration optimized for Bengali and English:
# - pageseg_devanagari_split_strategy=1 & ocr_devanagari_split_strategy=1:
#   Splits the continuous Bengali 'matra' (মাত্রা / shiro-rekha), enabling proper detection of BOLD Bengali text.
# - preserve_interword_spaces=1:
#   Maintains spacing between options (e.g. ক) ... খ) ...).
DEFAULT_TESSERACT_CONFIG = (
    r"--oem 3 --psm 6 "
    r"-c pageseg_devanagari_split_strategy=1 "
    r"-c ocr_devanagari_split_strategy=1 "
    r"-c preserve_interword_spaces=1"
)


def setup_tesseract_path(custom_cmd: str = None):
    """
    Locates the tesseract executable and configures TESSDATA_PREFIX.
    Checks:
      1. Explicit parameter if provided
      2. Environment variable 'TESSERACT_CMD'
      3. System PATH
      4. Standard Windows install locations
    """
    if pytesseract is None:
        return

    if custom_cmd and os.path.isfile(custom_cmd):
        pytesseract.pytesseract.tesseract_cmd = custom_cmd
        tessdata_dir = os.path.join(os.path.dirname(custom_cmd), "tessdata")
        if os.path.isdir(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
            os.environ["TESSDATA_PREFIX"] = tessdata_dir
        return

    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and os.path.isfile(env_cmd):
        pytesseract.pytesseract.tesseract_cmd = env_cmd
        tessdata_dir = os.path.join(os.path.dirname(env_cmd), "tessdata")
        if os.path.isdir(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
            os.environ["TESSDATA_PREFIX"] = tessdata_dir
        return

    # Check if tesseract is accessible via PATH
    which_path = shutil.which("tesseract")
    if which_path:
        tessdata_dir = os.path.join(os.path.dirname(which_path), "tessdata")
        if os.path.isdir(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
            os.environ["TESSDATA_PREFIX"] = tessdata_dir
        return

    # Check standard Windows paths
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
    ]

    for path in possible_paths:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            tessdata_dir = os.path.join(os.path.dirname(path), "tessdata")
            if os.path.isdir(tessdata_dir) and "TESSDATA_PREFIX" not in os.environ:
                os.environ["TESSDATA_PREFIX"] = tessdata_dir
            return


# Auto-configure tesseract path upon module import
setup_tesseract_path()


def resolve_crop_px(val, total_dimension: int) -> int:
    """
    Resolves a crop value to pixel count.
    Supports:
      - float or int < 1.0 (e.g. 0.35 -> 35% ratio of total_dimension)
      - string percentage (e.g. '35%' -> 35% ratio)
      - int/float >= 1.0 (e.g. 800 -> 800 pixels)
    """
    if val is None:
        return 0
    if isinstance(val, str):
        val = val.strip()
        if val.endswith("%"):
            ratio = float(val[:-1]) / 100.0
            return int(total_dimension * ratio)
        val = float(val)

    if isinstance(val, (int, float)):
        if 0.0 < val < 1.0:
            return int(total_dimension * val)
        return int(val)
    return 0


def crop_top_bottom(img, crop_top=100, crop_bottom=80):
    """
    Crops unwanted margins/headers at the top and footers at the bottom of the page image.
    Supports either pixel count (>= 1.0) or ratio/percentage (< 1.0 or '35%').

    :param img: PIL Image object.
    :param crop_top: Pixels or ratio to remove from top.
    :param crop_bottom: Pixels or ratio to remove from bottom.
    :return: Cropped PIL Image.
    """
    width, height = img.size
    top = max(0, min(resolve_crop_px(crop_top, height), height - 1))
    bottom = max(top + 1, height - max(0, resolve_crop_px(crop_bottom, height)))
    return img.crop((0, top, width, bottom))


def split_page_image(img, split_mode: str = "columns", split_ratio: float = 0.5):
    """
    Splits a page image into sub-images before running OCR.

    :param img: PIL Image object.
    :param split_mode:
        - 'columns' / 'horizontal' / 'left-right': splits vertically into Left & Right halves (for 2-column documents).
        - 'rows' / 'vertical' / 'top-bottom': splits horizontally into Top & Bottom halves.
        - 'none': returns the full image without splitting.
    :param split_ratio: Position of the split cut (default: 0.5 = 50% midpoint).
    :return: List of PIL Image objects in logical reading order.
    """
    mode = str(split_mode).lower().strip() if split_mode else "none"
    width, height = img.size

    if mode in ("columns", "horizontal", "left-right", "col", "cols", "2"):
        # Split into Left and Right halves (reading Left column first, then Right column)
        split_x = int(width * split_ratio)
        left_half = img.crop((0, 0, split_x, height))
        right_half = img.crop((split_x, 0, width, height))
        return [left_half, right_half]

    elif mode in ("rows", "vertical", "top-bottom", "row"):
        # Split into Top and Bottom halves
        split_y = int(height * split_ratio)
        top_half = img.crop((0, 0, width, split_y))
        bottom_half = img.crop((0, split_y, width, height))
        return [top_half, bottom_half]

    # No split
    return [img]


def extract_text_from_pdf(
    pdf_path: str,
    dpi: int = 200,
    lang: str = "ben+eng",
    custom_config: str = DEFAULT_TESSERACT_CONFIG,
    crop_top=100,
    crop_bottom=80,
    crop_top_first=0.35,
    crop_bottom_first=None,
    split: str = "columns",
    split_ratio: float = 0.5,
    debug_break: bool = True,
    debug_dir: str = "debug_images",
    tesseract_cmd: str = None,
    on_page_progress=None
) -> str:
    """
    Extracts text from a given PDF using PyMuPDF and pytesseract OCR.
    1. Applies dedicated crop ratio/pixels for Page 1 (header banners) and regular crop for subsequent pages.
    2. Splits image into columns/sections.
    3. Saves preview images and halts at 'break' if debug_break=True.
    4. Runs OCR (with Devanagari/Bengali shiro-rekha split for bold text) and formats extracted text.

    :param pdf_path: Path to the PDF file.
    :param dpi: Resolution for rasterizing PDF pages to images (default: 200).
    :param lang: Tesseract language codes (e.g. 'ben+eng' for Bengali & English).
    :param custom_config: Tesseract configuration flags.
    :param crop_top: Pixels or ratio to crop from the top for regular pages (default: 100).
    :param crop_bottom: Pixels or ratio to crop from the bottom for regular pages (default: 80).
    :param crop_top_first: Crop ratio or pixels specifically for Page 1 (default: 0.35 = 35% ratio).
    :param crop_bottom_first: Crop for bottom of Page 1 (defaults to crop_bottom if None).
    :param split: 'columns' (left/right), 'rows' (top/bottom), or 'none'.
    :param split_ratio: Cut position ratio (default: 0.5).
    :param debug_break: If True, saves preview images for Page 1 and Page 2 then breaks before OCR.
    :param debug_dir: Directory where debug preview images are saved (default: 'debug_images').
    :param tesseract_cmd: Optional custom path to tesseract.exe.
    :param on_page_progress: Optional callback function(current_page, total_pages).
    :return: Full extracted text formatted with page headers.
    """
    if fitz is None or Image is None or pytesseract is None:
        missing = []
        if fitz is None:
            missing.append("PyMuPDF (fitz)")
        if Image is None:
            missing.append("Pillow (PIL)")
        if pytesseract is None:
            missing.append("pytesseract")
        raise ImportError(
            f"Missing required Python libraries: {', '.join(missing)}.\n"
            f"Please install them via: pip install PyMuPDF Pillow pytesseract"
        )

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    setup_tesseract_path(tesseract_cmd)

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RuntimeError(f"Could not open PDF file '{pdf_path}': {e}")

    total_pages = len(doc)
    extracted_pages = []

    try:
        for page_index in range(total_pages):
            page = doc[page_index]
            
            # 1. Render page to image
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            # 2. Select appropriate crop for Page 1 vs subsequent pages
            if page_index == 0:
                c_top = crop_top_first if crop_top_first is not None else crop_top
                c_bottom = crop_bottom_first if crop_bottom_first is not None else crop_bottom
            else:
                c_top = crop_top
                c_bottom = crop_bottom

            # 3. Crop top and bottom margins before splitting
            img_cropped = crop_top_bottom(img, crop_top=c_top, crop_bottom=c_bottom)

            # 4. Split cropped image into sections (e.g. Left & Right columns)
            image_sections = split_page_image(img_cropped, split_mode=split, split_ratio=split_ratio)

            # 5. Save preview images so you can inspect them first
            if debug_break and page_index < 2:
                os.makedirs(debug_dir, exist_ok=True)
                orig_file = os.path.join(debug_dir, f"page_{page_index + 1}_original.png")
                cropped_file = os.path.join(debug_dir, f"page_{page_index + 1}_cropped_top_bottom.png")
                
                img.save(orig_file)
                img_cropped.save(cropped_file)

                crop_info = f"top={c_top}, bottom={c_bottom}"
                if page_index == 0:
                    crop_info += " [FIRST PAGE SEPARATE CROP]"
                else:
                    crop_info += " [REGULAR PAGE CROP]"

                print(f"\n[DEBUG] Preview images saved for Page {page_index + 1} ({crop_info}) in '{debug_dir}/':")
                print(f"  1. Original: {orig_file}")
                print(f"  2. Cropped : {cropped_file}")
                
                for idx, part_img in enumerate(image_sections, 1):
                    part_file = os.path.join(debug_dir, f"page_{page_index + 1}_part_{idx}.png")
                    part_img.save(part_file)
                    print(f"  3.{idx} Split part {idx}: {part_file}")

                # If we've processed Page 1 (and Page 2 if available), break before OCR
                if page_index == min(1, total_pages - 1):
                    # =========================================================================
                    # BREAK STATEMENT: Stops here before extracting text so you can inspect!
                    # (To continue full OCR, pass --no-break flag or comment out 'break')
                    # =========================================================================
                    print("\n[DEBUG] Paused at break statement before text extraction. Please inspect the images above.")
                    break
                else:
                    continue

            # 6. Extract text via OCR
            section_texts = []
            for part_img in image_sections:
                text = pytesseract.image_to_string(part_img, lang=lang, config=custom_config)
                if text.strip():
                    section_texts.append(text.strip())

            combined_page_text = "\n\n".join(section_texts)
            page_header = f"--- Page {page_index + 1} ---"
            extracted_pages.append(f"\n{page_header}\n{combined_page_text}\n")

            if on_page_progress:
                on_page_progress(page_index + 1, total_pages)

    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract is not installed or not in your system PATH.\n"
            "Please ensure Tesseract OCR is installed at 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'."
        )
    finally:
        doc.close()

    return "".join(extracted_pages)
