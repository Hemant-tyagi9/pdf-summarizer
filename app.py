from flask import Flask, render_template, request, jsonify, send_file, flash, redirect
import fitz  # PyMuPDF
import os
import json
from datetime import datetime
from fpdf import FPDF
import cohere

app = Flask(__name__, template_folder='templates')  # Explicitly set template folder
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = 'your_secret_key'  # Change this for production!

# Ensure directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("summaries", exist_ok=True)

# --- Cohere Setup ---
cohere_api_key = "IpxWRD7rwLgJyqlTBLS2zFxzMvZ2nMGJPneQn1Ev"  # Replace with env var in production
cohere_client = cohere.Client(cohere_api_key)

# --- Helper Functions ---
def get_summary(text):
    """Generate summary using Cohere API."""
    try:
        response = cohere_client.generate(
            model="command",
            prompt=f"Summarize this:\n\n{text[:12000]}\n\nSummary:",  # Truncate to avoid token limits
            max_tokens=300,
            temperature=0.5
        )
        return response.generations[0].text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def save_summary_to_history(title, summary):
    """Save summary to JSON history file."""
    history_file = "summaries/history.json"
    entry = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "title": title,
        "summary": summary,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)
    
    history.append(entry)
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)

def generate_pdf(summary, filename="summary.pdf"):
    """Convert summary to PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="PDF Summary", ln=1, align='C')
    pdf.multi_cell(0, 10, txt=summary)
    pdf_path = os.path.join("summaries", filename)
    pdf.output(pdf_path)
    return pdf_path

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle file upload
        file = request.files['pdf']
        if not file:
            flash("No file uploaded!")
            return redirect(request.url)
        
        # Save file
        filename = file.filename
        filepath = os.path.join("uploads", filename)
        file.save(filepath)
        
        # Extract text from PDF
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # Generate and save summary
        summary = get_summary(text)
        save_summary_to_history(filename, summary)
        
        return render_template('index.html', 
                           summary=summary, 
                           filename=filename)
    
    return render_template('index.html')  # GET request

@app.route('/history')
def history():
    """Return summary history as JSON."""
    history_file = "summaries/history.json"
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route('/download/<format>/<filename>')
def download(format, filename):
    """Download summary as TXT or PDF."""
    summary = request.args.get('summary', '')
    if format == 'txt':
        path = os.path.join("summaries", f"{filename}.txt")
        with open(path, 'w') as f:
            f.write(summary)
        return send_file(path, as_attachment=True)
    elif format == 'pdf':
        path = generate_pdf(summary, f"{filename}.pdf")
        return send_file(path, as_attachment=True)
    return "Invalid format", 400

# --- Run the App ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)  # Render requires host 0.0.0.0
