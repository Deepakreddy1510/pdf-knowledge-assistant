import fitz


def extract_text(pdf_path):
    """
    Extract text from every page of a PDF.
    """

    document = fitz.open(pdf_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text