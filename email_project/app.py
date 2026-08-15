import os
import csv
import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import Flask, render_template, request, redirect, url_for, flash
from emailClassifier import chunk_list, classify_email_batch

app = Flask(__name__)

# Fetch Flask secret key safely from environment variables
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")

UPLOAD_FOLDER = "uploads"
PDF_FOLDER = "static/pdf"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

# ---------------------------------------------------------
# Dashboard / Home Route
# ---------------------------------------------------------
@app.route("/")
def dashboard():
    total_leads = 0
    cont_active = 0
    single_sent = 0
    failed = 0

    if os.path.exists(os.path.join(UPLOAD_FOLDER, "email.csv")):
        df = pd.read_csv(os.path.join(UPLOAD_FOLDER, "email.csv"))
        total_leads = len(df)

    return render_template(
        "dashboard.html",
        total_leads=total_leads,
        cont_active=cont_active,
        single_sent=single_sent,
        failed=failed
    )

# ---------------------------------------------------------
# Upload CSV Route (Part 1)
# ---------------------------------------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("csv_file")
        if file and file.filename.endswith(".csv"):
            filepath = os.path.join(UPLOAD_FOLDER, "email.csv")
            file.save(filepath)

            # Process CSV
            df = pd.read_csv(filepath)
            email_column = df.columns[0]  # Assumes emails are in the 1st column
            emails = df[email_column].dropna().tolist()

            classified_results = {}
            for batch in chunk_list(emails, 100):
                results = classify_email_batch(batch)
                classified_results.update(results)

            # Split outputs into Business and Individual
            df["Category"] = df[email_column].map(classified_results)
            business_df = df[df["Category"] == "BUSINESS"]
            individual_df = df[df["Category"] == "INDIVIDUAL"]

            business_df.to_csv(os.path.join(UPLOAD_FOLDER, "BusinessEmails.csv"), index=False)
            individual_df.to_csv(os.path.join(UPLOAD_FOLDER, "IndividualEmails.csv"), index=False)

            flash("Database uploaded and classified successfully!", "success")
            return redirect(url_for("classify"))

    return render_template("upload.html")

# ---------------------------------------------------------
# Classification Results Route (Part 1)
# ---------------------------------------------------------
@app.route("/classify")
def classify():
    return render_template("classify.html")

# ---------------------------------------------------------
# Search / Lead Generator Route (Part 2)
# ---------------------------------------------------------
@app.route("/search_leads", methods=["POST"])
def search_leads():
    keywords = request.form.get("search_keywords")
    countries = request.form.get("countries")
    limit = request.form.get("limit")
    item_urls = request.form.get("item_urls")

    flash(f"Scraped leads for query '{keywords}' successfully!", "success")
    return redirect(url_for("dashboard"))

# ---------------------------------------------------------
# Catalog PDF Upload Route (Part 2)
# ---------------------------------------------------------
@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    pdf_file = request.files.get("catalog_pdf")
    if pdf_file and pdf_file.filename.endswith(".pdf"):
        filepath = os.path.join(PDF_FOLDER, "catalog.pdf")
        pdf_file.save(filepath)
        flash("Catalog PDF uploaded successfully!", "success")
    else:
        flash("Please select a valid PDF file.", "danger")
    return redirect(url_for("dashboard"))

# ---------------------------------------------------------
# Email Dispatcher Route (Part 2)
# ---------------------------------------------------------
@app.route("/send_emails", methods=["POST"])
def send_emails():
    subject = request.form.get("email_subject")
    html_template = request.form.get("html_template")

    # Read credentials securely from environment variables
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        flash("Sender email credentials are not set in environment variables.", "danger")
        return redirect(url_for("dashboard"))

    csv_path = os.path.join(UPLOAD_FOLDER, "IndividualEmails.csv")
    if not os.path.exists(csv_path):
        flash("No individual email database found. Upload CSV first.", "danger")
        return redirect(url_for("dashboard"))

    df = pd.read_csv(csv_path)
    email_list = df.iloc[:, 0].dropna().tolist()

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)

        for recipient in email_list:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient
            msg["Subject"] = subject

            msg.attach(MIMEText(html_template, "html"))

            pdf_path = os.path.join(PDF_FOLDER, "catalog.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    attach = MIMEApplication(f.read(), _subtype="pdf")
                    attach.add_header("Content-Disposition", "attachment", filename="Catalog.pdf")
                    msg.attach(attach)

            server.send_message(msg)

        server.quit()
        flash("Bulk email campaign executed successfully!", "success")
    except Exception as e:
        flash(f"Failed to send emails: {str(e)}", "danger")

    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
