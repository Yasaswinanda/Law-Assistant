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
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 16MB
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
        raw_topics = data.get('topics', '')
        topics = [t.strip() for t in raw_topics.split(',')] if isinstance(raw_topics, str) else [t.strip() for t in raw_topics]
        batch_size = max(1, int(data.get('batch_size', 1)))

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
                    body {{ 
                        font-family: Arial, sans-serif; 
                        line-height: 1.6; 
                        margin: 2cm; 
                    }}
                    h1, h2, h3 {{
                        color: #2c3e50;
                        margin-top: 1.5em;
                    }}
                    pre {{
                        background-color: #f8f9fa;
                        padding: 1em;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    code {{
                        background-color: #f8f9fa;
                        padding: 0.2em 0.4em;
                        border-radius: 3px;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1em 0;
                    }}
                    th, td {{
                        border: 1px solid #dfe2e5;
                        padding: 0.5em;
                        text-align: left;
                    }}
                    @media print {{
                        body {{ margin: 1cm; }}
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
