from flask import Flask, render_template, request, jsonify, send_file, flash, redirect
import fitz  # PyMuPDF
import os
import json
from datetime import datetime
from fpdf import FPDF
import cohere

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = 'your_secret_key'

# Ensure directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("summaries", exist_ok=True)

MAX_FILE_SIZE_MB = 10  # Free plan limit

# Direct API key (for local testing only)
cohere_api_key = "IpxWRD7rwLgJyqlTBLS2zFxzMvZ2nMGJPneQn1Ev"
cohere_client = cohere.Client(cohere_api_key)

def get_summary(text):
    prompt = f"Summarize the following text:\n\n"

    # Truncate to ensure the total prompt stays within 4000 tokens (~13,000 chars)
    max_chars = 12000  # safe limit
    truncated_text = text[:max_chars]

    full_prompt = prompt + truncated_text + "\n\nSummary:"

    try:
        response = cohere_client.generate(
            model="command",
            prompt=full_prompt,
            max_tokens=300,
            temperature=0.5,
            stop_sequences=["--"]
        )
        return response.generations[0].text.strip()
    except Exception as e:
        return f"Error summarizing with Cohere: {str(e)}"

def save_summary_to_history(title, summary):
    history_file = "summaries/history.json"
    entry = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "title": title,
        "summary": summary,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history = json.load(f)
        else:
            history = []

        history.append(entry)

        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving to history: {str(e)}")

def generate_pdf(summary, filename="summary.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="PDF Summary", ln=1, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for line in summary.split('\n'):
        pdf.multi_cell(0, 10, txt=line)

    pdf_path = os.path.join("summaries", filename)
    pdf.output(pdf_path)
    return pdf_path

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ''
    extracted_text = ''
    filename = ''

    if request.method == 'POST':
        file = request.files['pdf']

        file.seek(0, 2)
        file_length = file.tell()
        file.seek(0)

        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_length > max_bytes:
            flash("File exceeds 10MB. Please upgrade to the Pro Plan to upload larger files.")
            return redirect(request.url)

        start_page = request.form.get('start_page')
        end_page = request.form.get('end_page')

        if file:
            filename = file.filename
            filepath = os.path.join("uploads", filename)
            file.save(filepath)

            doc = fitz.open(filepath)

            try:
                start = int(start_page) - 1 if start_page else 0
                end = int(end_page) if end_page else len(doc)
            except ValueError:
                start, end = 0, len(doc)

            selected_text = ""
            for page_num in range(start, min(end, len(doc))):
                selected_text += doc[page_num].get_text()

            extracted_text = selected_text.strip()

            try:
                summary = get_summary(extracted_text[:100_000])
                if summary:
                    save_summary_to_history(filename, summary)
            except Exception as e:
                summary = f"Error summarizing: {str(e)}"

            doc.close()

    return render_template('index.html', 
                       summary=summary, 
                       extracted_text=extracted_text,
                       filename=filename)

@app.route('/history')
def get_history():
    history_file = "summaries/history.json"
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)
        return jsonify(history)
    return jsonify([])

@app.route('/delete_summary/<summary_id>', methods=['DELETE'])
def delete_summary(summary_id):
    history_file = "summaries/history.json"
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            history = json.load(f)

        updated_history = [entry for entry in history if entry['id'] != summary_id]

        with open(history_file, "w") as f:
            json.dump(updated_history, f, indent=2)

        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route('/download_txt/<filename>')
def download_txt(filename):
    summary = request.args.get('summary', '')
    txt_path = os.path.join("summaries", f"{filename}_summary.txt")
    with open(txt_path, "w") as f:
        f.write(summary)
    return send_file(txt_path, as_attachment=True)

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    summary = request.args.get('summary', '')
    pdf_path = generate_pdf(summary, f"{filename}_summary.pdf")
    return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
