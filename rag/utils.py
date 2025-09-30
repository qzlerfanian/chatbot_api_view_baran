import fitz  # PyMuPDF
import numpy as np
from .models import FileChunk
from django.conf import settings
from openai import OpenAI


client =OpenAI(api_key= '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',
timeout=30
)  # ← کلید API اینجا قرار می‌گیره یا از env

def extract_text_from_pdf(path):
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def chunk_text(text, max_words=150):
    words = text.split()
    return [' '.join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

def get_embedding(text):
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def create_chunks_and_embeddings(uploaded_file):
    chunks = chunk_text(uploaded_file.extracted_text)
    for chunk in chunks:
        emb = get_embedding(chunk)
        FileChunk.objects.create(
            uploaded_file=uploaded_file,
            content=chunk,
            embedding=emb
        )

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_relevant_chunks(query, user, top_k=5):
    query_emb = get_embedding(query)
    chunks = FileChunk.objects.filter(uploaded_file__user=user)
    scored = [(chunk, cosine_similarity(chunk.embedding, query_emb)) for chunk in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [item[0] for item in scored[:top_k]]

#----------------------------------

