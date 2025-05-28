from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, send_from_directory
import fitz  # PyMuPDF
import os
import json
from datetime import datetime
from fpdf import FPDF
import cohere

# Initialize Flask app with root as static folder
app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'your_secret_key_here'  # Change this for production!

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB file limit
UPLOAD_FOLDER = 'uploads'
SUMMARY_FOLDER = 'summaries'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

# Initialize Cohere client
cohere_client = cohere.Client("your_cohere_api_key_here")  # Replace with your key

def get_summary(text):
    """Generate summary using Cohere API"""
    try:
        response = cohere_client.generate(
            model="command",
            prompt=f"Summarize this document:\n\n{text[:12000]}\n\nSummary:",
            max_tokens=300,
            temperature=0.5
        )
        return response.generations[0].text.strip()
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def save_summary_to_history(title, summary):
    """Save summary to history JSON file"""
    history_file = os.path.join(SUMMARY_FOLDER, 'history.json')
    entry = {
        'id': datetime.now().strftime("%Y%m%d%H%M%S"),
        'title': title,
        'summary': summary,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    history = []
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
    
    history.append(entry)
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

def generate_pdf(summary, filename):
    """Generate PDF from summary text"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Document Summary", ln=1, align='C')
    pdf.multi_cell(0, 10, txt=summary)
    pdf_path = os.path.join(SUMMARY_FOLDER, filename)
    pdf.output(pdf_path)
    return pdf_path

@app.route('/')
def home():
    """Serve the main index.html file"""
    return send_file('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    """Handle PDF upload and summarization"""
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Save uploaded file
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Extract text from PDF
    try:
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        return jsonify({'error': f'PDF processing failed: {str(e)}'}), 500
    
    # Generate summary
    summary = get_summary(text)
    save_summary_to_history(filename, summary)
    
    return jsonify({
        'filename': filename,
        'summary': summary
    })

@app.route('/history')
def history():
    """Get summary history"""
    history_file = os.path.join(SUMMARY_FOLDER, 'history.json')
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/download/<format>/<filename>')
def download(format, filename):
    """Download summary in specified format"""
    summary = request.args.get('summary', '')
    if not summary:
        return jsonify({'error': 'No summary provided'}), 400
    
    if format == 'txt':
        txt_path = os.path.join(SUMMARY_FOLDER, f"{filename}.txt")
        with open(txt_path, 'w') as f:
            f.write(summary)
        return send_file(txt_path, as_attachment=True)
    elif format == 'pdf':
        pdf_path = generate_pdf(summary, f"{filename}.pdf")
        return send_file(pdf_path, as_attachment=True)
    else:
        return jsonify({'error': 'Invalid format'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)
