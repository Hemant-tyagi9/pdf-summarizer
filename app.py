import fitz  # PyMuPDF
import requests
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

API_KEY = "IpxWRD7rwLgJyqlTBLS2zFxzMvZ2nMGJPneQn1Ev"
AI_SUMMARY_API_URL = "https://api.your-ai-service.com/v1/summarize"  # Replace with your actual AI endpoint


def extract_text_from_pdf(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream.read(), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print("PDF extraction error:", e)
        return None


def summarize_text(text, language="english"):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "language": language
    }
    try:
        response = requests.post(AI_SUMMARY_API_URL, json=data, headers=headers, timeout=20)
        response.raise_for_status()
        json_data = response.json()
        # Assuming the summary is in json_data['summary'], adjust if API is different
        return json_data.get("summary", "No summary returned by API.")
    except Exception as e:
        print("AI summary API error:", e)
        return None


@app.route("/", methods=["POST"])
def generate_summary():
    if "pdf" not in request.files:
        return "No PDF file uploaded", 400

    pdf_file = request.files["pdf"]
    if pdf_file.filename == "" or not pdf_file.filename.lower().endswith(".pdf"):
        return "Invalid file type. Please upload a PDF.", 400

    language = request.form.get("language", "english").lower()
    if language not in ["english", "hindi"]:
        language = "english"  # default fallback

    text = extract_text_from_pdf(pdf_file)
    if not text:
        return "Failed to extract text from PDF.", 500

    summary = summarize_text(text, language)
    if not summary:
        return "Failed to generate summary from AI service.", 500

    return summary, 200, {"Content-Type": "text/plain; charset=utf-8"}


if __name__ == "__main__":
    app.run(debug=False, port=5000)
