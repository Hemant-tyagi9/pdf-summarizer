import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF
import tempfile
import requests

app = Flask(__name__)
CORS(app)

# Get the API key from environment variable
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_API_URL = "https://api.cohere.ai/v1/generate"

def extract_text_from_pdf(file_path, start_page, end_page):
    text = ""
    with fitz.open(file_path) as doc:
        for page_num in range(start_page - 1, min(end_page, len(doc))):
            text += doc[page_num].get_text()
    return text.strip()

def generate_summary(text, language="english", length="short", bullets=False):
    prompt = f"Summarize this PDF content in {language} in a {length} way."
    if bullets:
        prompt += " Use bullet points."

    prompt += f"\n\nText:\n{text}\n\nSummary:\n"

    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": "command-r-plus",
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.5,
    }

    response = requests.post(COHERE_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("generations", [{}])[0].get("text", "").strip()
    else:
        return f"Error from Cohere: {response.status_code}"

@app.route("/summarize", methods=["POST"])
def summarize():
    if "pdf" not in request.files:
        return jsonify({"error": "No PDF uploaded"}), 400

    pdf_file = request.files["pdf"]
    language = request.form.get("language", "english")
    start_page = int(request.form.get("startPage", 1))
    end_page = int(request.form.get("endPage", 1))
    summary_length = request.form.get("summaryLength", "short")
    bullet_points = request.form.get("bulletPoints", "false") == "true"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_file.save(tmp.name)
        pdf_path = tmp.name

    try:
        extracted_text = extract_text_from_pdf(pdf_path, start_page, end_page)
        summary = generate_summary(extracted_text, language, summary_length, bullet_points)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(pdf_path)

    return jsonify({
        "language": language,
        "extractedText": extracted_text,
        "summary": summary
    })

@app.route("/")
def home():
    return "PDF SmartNotes API is running."

if __name__ == "__main__":
    app.run(debug=True)
