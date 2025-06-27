import os
import google.generativeai as genai
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import hashlib

# Configuration
genai.configure(api_key=os.environ["GEMINI_API_KEY_GENERATE"])
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Update path as needed

class VectorStore:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)
        self.metadata = []
        
    def add_document(self, text, metadata):
        embeddings = self.model.encode(text)
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        self.index.add(embeddings)
        self.metadata.extend([metadata]*len(embeddings))

    def search(self, query, k=5):
        query_embedding = self.model.encode(query).reshape(1, -1)
        distances, indices = self.index.search(query_embedding, k)
        return [(self.metadata[idx], float(distances[0][i])) 
                for i, idx in enumerate(indices[0])]

def extract_text_with_ocr(pdf_path, page_num):
    images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
    text = pytesseract.image_to_string(images[0])
    return text

def process_pdf_page(page, pdf_path, page_num):
    try:
        text = page.extract_text()
        if len(text) < 200:  # Heuristic for potential image-based page
            return extract_text_with_ocr(pdf_path, page_num)
        return text
    except Exception as e:
        return extract_text_with_ocr(pdf_path, page_num)

def process_pdf_directory(directory_path, vector_store):
    pdf_contents = []
    
    for filename in os.listdir(directory_path):
        if filename.lower().endswith('.pdf'):
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, "rb") as f:
                    reader = PdfReader(f)
                    doc_id = hashlib.md5(filename.encode()).hexdigest()[:8]
                    full_text = []
                    
                    for page_num, page in enumerate(reader.pages):
                        text = process_pdf_page(page, file_path, page_num)
                        full_text.append(text)
                        
                        # Add to vector store with doc_text
                        vector_store.add_document(text, {
                            'doc_id': doc_id,
                            'filename': filename,
                            'page': page_num+1,
                            'doc_text': text  # THIS WAS MISSING
                        })
                    
                    pdf_contents.append({
                        'doc_id': doc_id,
                        'filename': filename,
                        'content': "\n".join(full_text),
                        'num_pages': len(reader.pages)
                    })
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    
    return pdf_contents

def generate_response(directory_path, user_input):
    vector_store = VectorStore()
    pdf_contents = process_pdf_directory(directory_path, vector_store)
    
    if not pdf_contents:
        return "No valid PDFs found in the directory"
    
    # Perform semantic search
    relevant_passages = vector_store.search(user_input, k=5)
    
    # Build context
    context = "RELEVANT PASSAGES:\n"
    for (meta, score) in relevant_passages:
        context += f"\nDocument: {meta['filename']} (Page {meta['page']})\n"
        context += f"Content: {meta['doc_text']}\n"
        context += f"Relevance Score: {score:.2f}\n{'-'*40}"
    
    SYSTEM_PROMPT = """
Act as an **expert note-taker and tutor**. Your task is to create **detailed, self-contained notes** from the provided source material that:  
1. **Teach core concepts**

**Follow these rules:**  
1. **Structure the Notes**:  
   - **Title**: Start with a title .  
   - **Sections**: Divide content into logical subsections using headers.  
   - **Key Content**:  
     - Define **terms** in simple language on first mention.  
     - Explain **cause-effect relationships**, **theories**, or **arguments** with examples.  
     - Use bullet points, tables for clarity.  

2. **Audience**: Notes are for a learner who wants to **master the material**, not just skim. Prioritize depth and clarity.  

3. **Style**:  
   - Avoid summaries or TL;DR sections.  
   - Use bold for key terms and italics for examples.  
   - Flag **common misconceptions** or **tricky points** in a *Note:* callout.  

4. **Answer Readiness**:  
   - If the material includes data, **simplify trends** (e.g., “Sales rose 30% in Q1 due to…”).  
    """
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        },
    )
    
    chat = model.start_chat(history=[])
    response = chat.send_message([
        SYSTEM_PROMPT,
        f"{context}\n\nUSER QUERY: {user_input}"
    ])
    
    return response.text

# Example usage
pdf_directory = "./pdfs"

# Query with semantic search
query = input("Enter a query : ")
response = generate_response(pdf_directory, query)
print(response)