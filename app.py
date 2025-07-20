from flask import Flask, jsonify, request, send_file
from werkzeug.utils import secure_filename
import os
import tempfile
from pdf2image import convert_from_path
import zipfile
import io
from flask_cors import CORS
from PyPDF2 import PdfMerger

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/')
def home():
    return jsonify({'message': 'Backend is running!'})

@app.route('/pdf-to-images', methods=['POST'])
def pdf_to_images():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File is not a PDF'}), 400

    filename = secure_filename(file.filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, filename)
        file.save(pdf_path)
        images = convert_from_path(pdf_path)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zipf:
            for i, img in enumerate(images):
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                zipf.writestr(f'page_{i+1}.png', img_bytes.read())
        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='images.zip')

@app.route('/images-to-pdf', methods=['POST'])
def images_to_pdf():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    files = request.files.getlist('files')
    if not files or len(files) == 0:
        return jsonify({'error': 'No files uploaded'}), 400

    images = []
    for file in files:
        if file.filename == '':
            continue
        img = None
        try:
            from PIL import Image
            img = Image.open(file.stream).convert('RGB')
        except Exception as e:
            continue
        images.append(img)

    if not images:
        return jsonify({'error': 'No valid images uploaded'}), 400

    pdf_bytes = io.BytesIO()
    images[0].save(pdf_bytes, format='PDF', save_all=True, append_images=images[1:])
    pdf_bytes.seek(0)
    return send_file(pdf_bytes, mimetype='application/pdf', as_attachment=True, download_name='output.pdf')

@app.route('/enhance-image', methods=['POST'])
def enhance_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    try:
        from PIL import Image, ImageOps
        img = Image.open(file.stream)
        enhanced_img = ImageOps.autocontrast(img)
        img_bytes = io.BytesIO()
        enhanced_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return send_file(img_bytes, mimetype='image/png', as_attachment=True, download_name='enhanced.png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/merge-pdf', methods=['POST'])
def merge_pdf():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    files = request.files.getlist('files')
    if not files or len(files) == 0:
        return jsonify({'error': 'No files uploaded'}), 400

    merger = PdfMerger()
    temp_files = []
    try:
        for file in files:
            if file.filename == '' or not file.filename.lower().endswith('.pdf'):
                continue
            temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            file.save(temp.name)
            temp.close()  # Close the file so it's not locked
            temp_files.append(temp.name)
            merger.append(temp.name)
        if not temp_files:
            return jsonify({'error': 'No valid PDF files uploaded'}), 400
        merged_pdf = io.BytesIO()
        merger.write(merged_pdf)
        merger.close()
        merged_pdf.seek(0)
        return send_file(merged_pdf, mimetype='application/pdf', as_attachment=True, download_name='merged.pdf')
    finally:
        for temp_path in temp_files:
            os.remove(temp_path)

