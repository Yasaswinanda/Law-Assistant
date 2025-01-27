import os
import hashlib
import numpy as np
import google.generativeai as genai
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
import pytesseract
from sentence_transformers import SentenceTransformer
import faiss

class VectorStore:
    """Handles document embeddings and semantic search"""
    _model = None  # Singleton embedding model
    
    def __init__(self):
        if VectorStore._model is None:
            VectorStore._model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)
        self.metadata = []

    def add_document(self, text, metadata):
        embeddings = self._model.encode(text)
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        self.index.add(embeddings)
        self.metadata.extend([metadata]*len(embeddings))

    def search(self, query, k=5):
        query_embedding = self._model.encode(query).reshape(1, -1)
        distances, indices = self.index.search(query_embedding, k)
        return [(self.metadata[idx], float(distances[0][i])) 
                for i, idx in enumerate(indices[0])]

class PDFProcessor:
    """Handles PDF text extraction with OCR fallback"""
    
    def __init__(self, tesseract_cmd=r'/usr/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _extract_with_ocr(self, pdf_path, page_num):
        try:
            images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
            return pytesseract.image_to_string(images[0])
        except Exception as e:
            print(f"OCR failed for {pdf_path} page {page_num}: {str(e)}")
            return ""

    def process_page(self, page, pdf_path, page_num):
        try:
            text = page.extract_text()
            if len(text) < 200:  # Heuristic for image-based page
                return self._extract_with_ocr(pdf_path, page_num)
            return text
        except Exception as e:
            return self._extract_with_ocr(pdf_path, page_num)

    def process_pdf(self, file_path):
        """Process a single PDF file"""
        doc_id = hashlib.md5(os.path.basename(file_path).encode()).hexdigest()[:8]
        contents = []
        
        with open(file_path, "rb") as f:
            reader = PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                text = self.process_page(page, file_path, page_num)
                contents.append({
                    'text': text,
                    'metadata': {
                        'doc_id': doc_id,
                        'filename': os.path.basename(file_path),
                        'page': page_num + 1
                    }
                })
        return contents

class NotesGenerator:
    """Handles note generation using Gemini API"""
    
    SYSTEM_PROMPT = ""
    
    def __init__(self, api_key, all_topics):
        self.all_topics = all_topics
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        SYSTEM_PROMPT = f"""Act as an **expert note-taker and tutor**. Your task is to create **detailed, self-contained notes** from the provided source material and your own knowledge that:  
1. **Teach core concepts**

**IMPORTANT NOTE** : You are only given a small amount of topics because of limitations in tocken size. So remember to stick strictly to the topics
**ALL TOPICS THAT ARE TO BE COVERED AS A WHOLE BUT NOT CURRENTLY DISCLOSED TO YOU ARE : ** {self.all_topics} \n
**THIS IS ONLY FOR YOUR REFERENCE FOR YOU TO BETTER STRUCTURE THE NOTES AND ENSURE THERE IS NO REPETATIONS OF ANY TOPICS**


**Follow these rules:**  
1. **Structure the Notes**:  
   - **Title**: Start with a title .  
   - **Sections**: Divide content into logical subsections using headers.  
   - **Key Content**:  
     - Use bullet points, tables for clarity.

2. **Audience**: Notes are for a learner who wants to understand the topics with consice points while also going into depth only where required. Prioritize depth and clarity.  

3. **Style**:  
   - Avoid summaries or TL;DR sections.  
   - Use bold for key terms and italics for examples.  
   - Flag **common misconceptions** or **tricky points** in a *Note:* callout.  

4. **Answer Readiness**:  
   - If the material includes data, **simplify trends** (e.g., “Sales rose 30% in Q1 due to…”)."""  

    def _build_context(self, relevant_passages):
        context = "RELEVANT PASSAGES:\n"
        for (meta, score) in relevant_passages:
            context += f"\nDocument: {meta['filename']} (Page {meta['page']})\n"
            context += f"Content: {meta['doc_text']}\n"
            context += f"Relevance Score: {score:.2f}\n{'-'*40}"
        return context

    def generate_notes(self, vector_store, base_prompt, topics):
        """Generate notes for multiple topics"""
        results = []
        for topic in topics:
            relevant_passages = vector_store.search(topic, k=10)
            context = self._build_context(relevant_passages)
            
            chat = self.model.start_chat(history=[])
            response = chat.send_message([
                self.SYSTEM_PROMPT,
                f"\n\nTOPIC: {topic}\n\n{context}" + "\n\n" + f"""
                **IMPORTANT NOTE** : You are only given a small amount of topics because of limitations in number of tockens that can be sent at once. So remember to stick strictly to the topics
**ALL TOPICS THAT ARE TO BE COVERED AS A WHOLE BUT NOT CURRENTLY DISCLOSED TO YOU ARE : ** {self.all_topics} \n
**THIS IS ONLY FOR YOUR REFERENCE FOR YOU TO BETTER STRUCTURE THE NOTES AND ENSURE THERE IS NO REPETATIONS OF ANY TOPICS**
**DONT ACTUALLY PROVIDE NOTES BASED ON THESE TOPICS AND ONLY GIVE THE ANSWER TO THE BASE PROMPT(even if it is present in all topics only answer the base prompt)\n""" + f"""\n BASE PROMPT: {base_prompt}"""
            ])
            results.append(response.text)
        return results