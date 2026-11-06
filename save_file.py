import os


def save_text(text: str, output_path: str, encoding: str = "utf-8") -> str:
    """
    Saves extracted text to a designated file path.
    Creates parent directories automatically if they do not exist.

    :param text: Text content to save.
    :param output_path: Destination file path.
    :param encoding: File encoding (default: utf-8).
    :return: Absolute path of the saved file.
    """
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, "w", encoding=encoding) as f:
        f.write(text)

    return os.path.abspath(output_path)


def save_extracted_file(text: str, filename: str, output_dir: str = "output") -> str:
    """
    Helper function to save text into an output directory with a given filename.

    :param text: Text content to save.
    :param filename: Desired filename (e.g. '32th bcs.txt').
    :param output_dir: Directory where the file should be saved (default: 'output').
    :return: Absolute path of the saved file.
    """
    if not os.path.splitext(filename)[1]:
        filename = f"{filename}.txt"

    target_path = os.path.join(output_dir, filename)
    return save_text(text, target_path)


def is_already_extracted(filename: str, output_dir: str = "output") -> bool:
    """
    Checks if an output text file already exists and is not empty.

    :param filename: Name of the output file (e.g. '32th bcs.txt').
    :param output_dir: Directory where output files reside.
    :return: True if the file exists and has size > 0, otherwise False.
    """
    if not os.path.splitext(filename)[1]:
        filename = f"{filename}.txt"

    target_path = os.path.join(output_dir, filename)
    return os.path.isfile(target_path) and os.path.getsize(target_path) > 0
