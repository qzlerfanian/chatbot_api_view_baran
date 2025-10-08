from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadForm
from .models import Upload
from .utils import ocr_image_file
from django.http import HttpResponse

# برای docx
try:
    from docx import Document
except ImportError:
    Document = None

# برای pdf
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:
    SimpleDocTemplate = None
    Paragraph = None
    getSampleStyleSheet = None
import io


def upload_view(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['file']
            obj = Upload.objects.create(file=f)
            text = ocr_image_file(obj.file)
            obj.extracted_text = text
            obj.save()
            return redirect('result', pk=obj.pk)
    else:
        form = UploadForm()
    return render(request, 'uploading.html', {'form': form})


def result_view(request, pk):
    obj = get_object_or_404(Upload, pk=pk)
    return render(request, 'result.html', {'obj': obj})


# ========================
# دانلود به صورت Word
# ========================
def download_docx(request, pk):
    obj = get_object_or_404(Upload, pk=pk)
    document = Document()
    document.add_paragraph(obj.extracted_text or "")

    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename=ocr_result_{pk}.docx'
    return response


# ========================
# دانلود به صورت PDF
# ========================
def download_pdf(request, pk):
    obj = get_object_or_404(Upload, pk=pk)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = [Paragraph(obj.extracted_text or "", styles["Normal"])]
    doc.build(story)

    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename=ocr_result_{pk}.pdf'
    return response