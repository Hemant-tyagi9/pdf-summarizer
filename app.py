from flask import Flask, render_template, request, jsonify, send_file
import fitz  # PyMuPDF
import os
import json
from datetime import datetime
from fpdf import FPDF
import cohere

# Flask setup
app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'IpxWRD7rwLgJyqlTBLS2zFxzMvZ2nMGJPneQn1Ev'

# Config
UPLOAD_FOLDER = 'uploads'
SUMMARY_FOLDER = 'summaries'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

# Cohere setup (✅ Replace with your key)
cohere_client = cohere.Client("IpxWRD7rwLgJyqlTBLS2zFxzMvZ2nMGJPneQn1Ev")

def get_summary(text):
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
    return send_file('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    try:
        doc = fitz.open(filepath)
        text = "".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        return jsonify({'error': f'PDF processing failed: {str(e)}'}), 500
    summary = get_summary(text)
    save_summary_to_history(filename, summary)
    return jsonify({'filename': filename, 'summary': summary})

@app.route('/download/<format>/<filename>')
def download(format, filename):
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
    app.run(host='0.0.0.0', port=10000)
