from PIL import Image
import tempfile
import os

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import ocrmypdf
except ImportError:
    ocrmypdf = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

# OCR با پشتیبانی فارسی (lang='fas')
def ocr_image_file(file_obj, lang='fas'):
    suffix = os.path.splitext(file_obj.name)[1].lower()
    text = ""

    if suffix in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
        image = Image.open(file_obj)
        text = pytesseract.image_to_string(image, lang=lang)

    elif suffix == '.pdf':
        # فایل موقت برای OCR
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as inp, tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as out:
            inp.write(file_obj.read())
            inp.flush()
            ocrmypdf.ocr(inp.name, out.name, force_ocr=True, language=lang)

            # استخراج متن از PDF خروجی
            reader = PdfReader(out.name)
            for page in reader.pages:
                text += page.extract_text() or ""

        # تمیز کردن فایل‌های موقت
        os.remove(inp.name)
        os.remove(out.name)

    return text
