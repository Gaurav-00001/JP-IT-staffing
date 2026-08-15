import google.generativeai as genai
import json

genai.configure(api_key="YOUR_GEMINI_API_KEY")

def chunk_list(lst, size):
    """Splits a list into smaller batches."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def classify_email_batch(emails):
    """
    Classifies up to 100 emails in a single Gemini request.
    Returns a dictionary: {"email@example.com": "BUSINESS", ...}
    """
    prompt = f"""
    You are an email classifier.
    Classify each email in the list below as either 'BUSINESS' or 'INDIVIDUAL'.

    BUSINESS:
    - Companies, Organizations, Schools, Academies, Institutes, Clinics, Shops, Support/Sales, Official contacts.

    INDIVIDUAL:
    - Personal email addresses (e.g., Gmail, Yahoo, Hotmail personal accounts).

    Emails to classify:
    {json.dumps(emails)}

    Respond strictly with valid JSON format mapping each email to its category:
    {{"email": "BUSINESS|INDIVIDUAL"}}
    """
    
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    try:
        return json.loads(response.text.strip())
    except Exception:
        return {email: "INDIVIDUAL" for email in emails}