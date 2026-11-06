import os
import sys
import re
import argparse
from typing import List

# Import our modular extraction and save functions
from extract import extract_text_from_pdf
from save_file import save_extracted_file, is_already_extracted


def natural_sort_key(s: str):
    """Sort strings containing numbers in human order (e.g. 10th, 11th, ..., 50th)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def get_all_pdf_files(search_dirs: List[str]) -> List[str]:
    """Scan search directories and return sorted list of unique PDF file paths."""
    found_files = []
    seen_names = set()

    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for fname in sorted(os.listdir(directory), key=natural_sort_key):
            if fname.lower().endswith(".pdf"):
                if fname not in seen_names:
                    seen_names.add(fname)
                    found_files.append(os.path.join(directory, fname))

    return found_files


def resolve_pdf_targets(file_arg: str, search_dirs: List[str]) -> List[str]:
    """
    Resolves user file input to matching PDF file paths.

    Supported formats:
      - 'all': matches all PDFs found in search directories
      - Number like '32': matches files with '32' (e.g. '32th bcs.pdf', '32 th bcs.pdf')
      - Filename like '50th bcs.pdf' or relative path 'pdf/50th bcs.pdf'
    """
    all_pdfs = get_all_pdf_files(search_dirs)

    # 1. Check for 'all'
    if file_arg.strip().lower() == "all":
        return all_pdfs

    # 2. Check if file_arg directly points to an existing file path
    if os.path.isfile(file_arg):
        return [file_arg]

    for directory in search_dirs:
        candidate = os.path.join(directory, file_arg)
        if os.path.isfile(candidate):
            return [candidate]
        if not candidate.lower().endswith(".pdf") and os.path.isfile(candidate + ".pdf"):
            return [candidate + ".pdf"]

    # 3. If file_arg is a number (e.g. '32' or '50')
    target_clean = file_arg.strip().lower()
    if target_clean.isdigit():
        number = target_clean
        # Match whole number token, e.g. 32th, 32 th, or surrounded by non-digits
        pattern = re.compile(rf"(?<!\d){re.escape(number)}(?!\d)", re.IGNORECASE)
        matched = [f for f in all_pdfs if pattern.search(os.path.basename(f))]
        if matched:
            return matched

    # 4. Fallback: substring match on filenames
    matched = [f for f in all_pdfs if target_clean in os.path.basename(f).lower()]
    if matched:
        return matched

    return []


def parse_arguments():
    """
    Parse command-line arguments.
    Also handles non-standard flags like 'file=32' or 'file=all'.
    """
    normalized_argv = []
    for arg in sys.argv[1:]:
        if arg.startswith("file="):
            normalized_argv.append(f"--{arg}")
        else:
            normalized_argv.append(arg)

    parser = argparse.ArgumentParser(
        description="Extract Bengali and English text from BCS PDF files using OCR.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Examples:
  python index.py --file=40
  python index.py --file=40 --no-break
  python index.py --file=40 --crop-top-first=0.35 --crop-top=100
  python index.py --file=all --no-break --skip-existing
"""
    )

    parser.add_argument(
        "-f", "--file",
        dest="file",
        required=False,
        default=None,
        help="PDF file number (e.g., 32), filename, or 'all' to process all files."
    )

    parser.add_argument(
        "-o", "--output-dir",
        dest="output_dir",
        default="output",
        help="Directory to save extracted text files (default: 'output')."
    )

    parser.add_argument(
        "-s", "--skip-existing",
        dest="skip_existing",
        action="store_true",
        help="Skip files that have already been extracted in the output directory."
    )

    parser.add_argument(
        "--crop-top-first",
        dest="crop_top_first",
        default="0.35",
        help="Top crop ratio or pixels specifically for Page 1 (default: 0.35 = 35%% ratio or 800px)."
    )

    parser.add_argument(
        "--crop-bottom-first",
        dest="crop_bottom_first",
        default=None,
        help="Bottom crop ratio or pixels for Page 1 (default: falls back to --crop-bottom)."
    )

    parser.add_argument(
        "--crop-top",
        dest="crop_top",
        default="100",
        help="Top crop pixels or ratio for regular pages (page 2 onwards, default: 100px)."
    )

    parser.add_argument(
        "--crop-bottom",
        dest="crop_bottom",
        default="80",
        help="Bottom crop pixels or ratio for regular pages (default: 80px)."
    )

    parser.add_argument(
        "--no-break",
        dest="no_break",
        action="store_true",
        help="Disable debug break statement to extract full document."
    )

    parser.add_argument(
        "--split",
        dest="split",
        default="columns",
        choices=["columns", "rows", "none", "horizontal", "vertical"],
        help="Split page before OCR: 'columns' (left/right, default for 2-column BCS PDFs), 'rows' (top/bottom), or 'none'."
    )

    parser.add_argument(
        "--split-ratio",
        dest="split_ratio",
        type=float,
        default=0.5,
        help="Split position ratio between 0.1 and 0.9 (default: 0.5 = 50%% center cut)."
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="DPI resolution for rendering PDF pages to image (default: 200)."
    )

    parser.add_argument(
        "--lang",
        default="ben+eng",
        help="Tesseract OCR language(s) (default: 'ben+eng')."
    )

    parser.add_argument(
        "--tesseract-cmd",
        dest="tesseract_cmd",
        default=None,
        help="Explicit path to tesseract executable if not in standard PATH."
    )

    return parser.parse_args(normalized_argv)


def main():
    args = parse_arguments()

    search_dirs = ["pdf", "."]
    all_available = get_all_pdf_files(search_dirs)

    if not all_available:
        print("[!] No PDF files found in 'pdf/' directory or current folder.")
        sys.exit(1)

    # If --file was not provided, show available options or help
    if not args.file:
        print("=" * 60)
        print(" BCS PDF OCR Extractor")
        print("=" * 60)
        print("Usage:")
        print("  python index.py --file=40")
        print("  python index.py --file=all --no-break")
        print("\nAvailable PDF files:")
        for idx, pdf_path in enumerate(all_available, 1):
            print(f"  [{idx:02d}] {os.path.basename(pdf_path)}")
        print("\nPlease specify a file using --file=<number|name|all>")
        return

    targets = resolve_pdf_targets(args.file, search_dirs)

    if not targets:
        print(f"[!] Could not find any PDF matching: '{args.file}'")
        print("Available PDFs:")
        for pdf_path in all_available:
            print(f"  - {os.path.basename(pdf_path)}")
        sys.exit(1)

    debug_break = not args.no_break

    print("=" * 60)
    print(f" Found {len(targets)} file(s) to process:")
    for t in targets:
        print(f"  -> {t}")
    print(f" Output folder  : {os.path.abspath(args.output_dir)}")
    print(f" Page 1 Top Crop: {args.crop_top_first} (Dedicated First Page Ratio)")
    print(f" Other Pages Top: {args.crop_top} | Bottom: {args.crop_bottom}")
    print(f" Page Split     : {args.split} (ratio: {args.split_ratio})")
    print(f" OCR Language   : {args.lang} | DPI: {args.dpi}")
    if debug_break:
        print(" Debug Mode     : ACTIVE (Saves Page 1 & 2 images & pauses at break)")
    if args.skip_existing:
        print(" Skip Existing  : Enabled")
    print("=" * 60)

    success_count = 0
    skipped_count = 0
    fail_count = 0

    for idx, pdf_path in enumerate(targets, 1):
        filename = os.path.basename(pdf_path)
        base_name, _ = os.path.splitext(filename)
        output_filename = f"{base_name}.txt"

        print(f"\n[{idx}/{len(targets)}] Processing '{filename}'...")

        if args.skip_existing and is_already_extracted(output_filename, args.output_dir):
            print(f"   [SKIPPED] Already extracted: '{output_filename}'")
            skipped_count += 1
            continue

        def progress_tracker(current, total):
            print(f"   -> OCR Page {current}/{total}...", end="\r", flush=True)

        try:
            extracted_text = extract_text_from_pdf(
                pdf_path=pdf_path,
                dpi=args.dpi,
                lang=args.lang,
                crop_top=args.crop_top,
                crop_bottom=args.crop_bottom,
                crop_top_first=args.crop_top_first,
                crop_bottom_first=args.crop_bottom_first,
                split=args.split,
                split_ratio=args.split_ratio,
                debug_break=debug_break,
                debug_dir="debug_images",
                tesseract_cmd=args.tesseract_cmd,
                on_page_progress=progress_tracker
            )
            print()  # newline after progress

            if extracted_text and extracted_text.strip():
                saved_path = save_extracted_file(
                    text=extracted_text,
                    filename=output_filename,
                    output_dir=args.output_dir
                )
                print(f"   [SUCCESS] Saved to: {saved_path}")
                success_count += 1
            else:
                if debug_break:
                    print(f"   [INFO] Paused at break statement. Check 'debug_images/' to review Page 1 and Page 2.")

        except Exception as e:
            print()
            print(f"   [ERROR] Failed to process '{filename}': {e}")
            fail_count += 1

    print("\n" + "=" * 60)
    print(" Execution Complete!")
    if debug_break:
        print(" -> Inspect the generated images inside 'debug_images/' folder.")
        print(" -> When satisfied, run with '--no-break' to extract all pages.")
    print("=" * 60)


if __name__ == "__main__":
    main()
