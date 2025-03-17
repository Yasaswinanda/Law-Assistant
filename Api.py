import os
import hashlib
import tempfile
import markdown
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from weasyprint import HTML
from processing import PDFProcessor, VectorStore, NotesGenerator
from document_cache import DocumentCache
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 2000 * 1024 * 1024  # 16MB
load_dotenv()

# Global state
vector_store = VectorStore()
processed_hashes = set()
pdf_processor = PDFProcessor()
document_cache = DocumentCache(ttl=3600)

@app.route('/upload', methods=['POST'])
def handle_upload():
    global vector_store, processed_hashes
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400

    uploaded_files = request.files.getlist('files')
    new_uploads = []

    for file in uploaded_files:
        if file.filename == '' or not file.filename.lower().endswith('.pdf'):
            continue

        try:
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            orig_filename = secure_filename(file.filename)

            if file_hash in processed_hashes:
                continue

            cached_data = document_cache.get_document(file_hash)
            if not cached_data:
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_hash}.pdf")
                with open(temp_path, 'wb') as f:
                    f.write(file_content)
                
                pages = pdf_processor.process_pdf(temp_path)
                os.remove(temp_path)
                document_cache.add_document(file_hash, pages)
                cached_data = pages

            for page in cached_data:
                metadata = {
                    'doc_id': file_hash,
                    'filename': orig_filename,
                    'page': page['metadata']['page'],
                    'doc_text': page['text']
                }
                vector_store.add_document(page['text'], metadata)

            processed_hashes.add(file_hash)
            new_uploads.append(orig_filename)

        except Exception as e:
            app.logger.error(f"Error processing {file.filename}: {str(e)}")
            return jsonify({'error': f"Failed to process {file.filename}"}), 500

    return jsonify({
        'message': f'Processed {len(new_uploads)} new files',
        'files': new_uploads
    })

@app.route('/generate', methods=['POST'])
def handle_generation():
    global vector_store

    if not processed_hashes:
        return jsonify({'error': 'No documents processed'}), 400

    data = request.json
    try:
        base_prompt = data.get('base_prompt', 'Generate comprehensive notes about:')
        topics = data.get('topics', '')
        batch_size = int(data.get('batch_size'))

        if not topics:
            return jsonify({'error': 'No topics provided'}), 400

        notes_generator = NotesGenerator(os.environ["GEMINI_API_KEY"], topics)
        results = []

        for i in range(0, len(topics), batch_size):
            batch = topics[i:i+batch_size]
            batch_results = notes_generator.generate_notes(
                vector_store,
                base_prompt=base_prompt,
                topics=batch
            )
            results.extend(batch_results)
        
        # Process content to remove topic headings
        processed_contents = []
        for topic, content in zip(topics, results):
            lines = content.split('\n')
            expected_heading = f'# {topic}'
            
            # Remove the topic heading if present
            if lines and lines[0].strip() == expected_heading:
                processed_content = '\n'.join(lines[1:])
            else:
                processed_content = content
            
            processed_contents.append(processed_content)

        # Combine all content into a single Markdown document
        full_markdown = '\n\n'.join(processed_contents)

        # Convert Markdown to HTML with enhanced formatting
        html_content = markdown.markdown(full_markdown, extensions=['extra'])
        
        # Add PDF styling
        styled_html = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    /* Define A4 page size and minimal margins for printing */
                    @page {{ size: A4; margin: 1cm; }}
                    body {{ 
                        font-family: Georgia, serif;
                        font-size: 12pt;
                        line-height: 1.5;
                        margin: 0;
                        padding: 1cm;
                        text-align: justify;
                        background: #fff;
                    }}
                    h1, h2, h3 {{
                        font-weight: bold;
                        margin-top: 1em;
                        margin-bottom: 0.5em;
                        border-bottom: 1px solid #ccc;
                        padding-bottom: 0.2em;
                    }}
                    h1 {{ color: #003366; }}  /* Deep navy blue */
                    h2 {{ color: #005B4F; }}  /* Dark teal */
                    h3 {{ color: #00796B; }}  /* Muted cyan */
                    pre {{
                        background-color: #f8f9fa;
                        padding: 0.5em;
                        border-radius: 5px;
                        overflow-x: auto;
                        font-size: 10pt;
                    }}
                    code {{
                        background-color: #f8f9fa;
                        padding: 0.2em 0.4em;
                        border-radius: 3px;
                        font-size: 10pt;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 0.5em 0;
                        font-size: 10pt;
                    }}
                    th, td {{
                        border: 1px solid #dfe2e5;
                        padding: 0.3em;
                        text-align: left;
                    }}
                    ul, ol {{
                        margin-left: 4px;  /* Minimum indentation */
                        padding-left: 4px;
                    }}
                    li {{
                        margin-bottom: 4px;
                    }}
                    b, strong {{
                        font-weight: bold;
                        color: #222; /* Dark gray for contrast */
                    }}
                    @media print {{
                        body {{ margin: 0; padding: 1cm; }}
                        pre {{ white-space: pre-wrap !important; }}
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
        </html>
        """

        # Generate PDF
        pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        HTML(string=styled_html).write_pdf(pdf_file.name)
        pdf_file.close()

        # Read PDF content and clean up
        with open(pdf_file.name, 'rb') as f:
            pdf_data = f.read()
        os.unlink(pdf_file.name)

        

        # Return PDF response
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment; filename="generated_notes.pdf"'}
        )
    
    except Exception as e:
        app.logger.error(f"Generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate notes'}), 500

@app.route('/reset', methods=['POST'])
def handle_reset():
    global vector_store, processed_hashes
    vector_store = VectorStore()
    processed_hashes = set()
    return jsonify({'message': 'System reset successfully'})

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
