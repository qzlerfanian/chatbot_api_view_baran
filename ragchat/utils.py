import io
from openai import OpenAI

# استفاده از متغیر محیطی بهتره
from django.conf import settings
client = OpenAI(api_key= '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'
)
def create_vector_store(file_obj, filename=None, vector_store_id=None):
    """
    - file_obj: file-like object (InMemoryUploadedFile یا BytesIO)
    - filename: اسم فایل (در صورت نیاز برای ایجاد vector store جدید)
    - vector_store_id: اگر موجود باشد، فایل به همان vector store اضافه می‌شود
    """
    # اگر فایل جنگو هست و هنوز BytesIO نیست
    if not isinstance(file_obj, io.IOBase):
        file_obj = io.BytesIO(file_obj.read())
        file_obj.name = filename or getattr(file_obj, "name", "file.txt")

    if vector_store_id:
        # آپلود به vector store موجود
        client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store_id,
            files=[file_obj]
        )
        return vector_store_id
    else:
        # ایجاد vector store جدید
        vs = client.vector_stores.create(name=filename or getattr(file_obj, "name", "file.txt"))
        client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vs.id,
            files=[file_obj]
        )
        return vs.id


def ask_file(vector_store_id, question):
    """
    ارسال سوال به فایل‌ها با ابزار file_search
    """
    response = client.responses.create(
        model="gpt-4.1",
        input=question,
        tools=[{
            "type": "file_search",
            "vector_store_ids": [vector_store_id]
        }]
    )

    # output_text ممکنه None باشه، پس امن گرفتن
    text = getattr(response, "output_text", None)
    if not text:
        try:
            text = response.output[0].content[0].text
        except (AttributeError, IndexError):
            text = str(response)
    return text
