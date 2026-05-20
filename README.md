# 🧾 MOELINVO
Professional invoice & receipt generator built with Streamlit, Playwright, and Google Drive storage.

## ✨ Features

* 🔐 Google Login protected admin dashboard
* 🧾 Professional PDF invoice generation
* ☁️ Google Drive cloud storage
* 📦 Bulk invoice JSON import
* 🔗 Public receipt sharing with secure token
* 📄 HTML invoice preview
* ✍️ Signature image embedding
* 🎨 Dynamic brand configuration via Google Drive
* 📱 WhatsApp / social media friendly receipt links
* 🚀 Streamlit Cloud deployment ready


## 🏗️ Tech Stack

* Python
* Streamlit
* Playwright
* Jinja2
* Google Drive API
* OAuth Authentication


## 📂 Project Structure

```bash
moelinvo/
├── app.py
├── style.css
├── requirements.txt
├── packages.txt
├── templates/
│   └── invoice_template.html
├── invoice/
│   ├── json/
│   ├── pdf/
│   └── receipts/
└── assets/
```


## ☁️ Google Drive Storage

MOELINVO stores invoices directly in Google Drive.

Recommended structure:

```bash
MOELINVO_STORAGE/
├── assets/
│   ├── brand_config.json
│   └── signature.png
├── invoices_json/
├── invoices_pdf/
└── receipts/
```


## 🔐 Streamlit Secrets Configuration

Create `.streamlit/secrets.toml`

```toml
ADMIN_EMAIL = "your@email.com"

GOOGLE_DRIVE_JSON_FOLDER_ID = "..."
GOOGLE_DRIVE_PDF_FOLDER_ID = "..."
GOOGLE_DRIVE_RECEIPT_FOLDER_ID = "..."
GOOGLE_DRIVE_ASSETS_FOLDER_ID = "..."

[google_oauth_token]
token = "..."
refresh_token = "..."
token_uri = "https://oauth2.googleapis.com/token"
client_id = "..."
client_secret = "..."
scopes = ["https://www.googleapis.com/auth/drive"]
```


## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/moelinvo.git
cd moelinvo
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Chromium

```bash
playwright install chromium
```


## 🚀 Run Locally

```bash
streamlit run app.py
```


## 🌐 Deployment

### Streamlit Cloud

Required files:

* `requirements.txt`
* `packages.txt`

Example `packages.txt`

```txt
chromium
```


## 🧾 Receipt System

Each invoice automatically generates:

* PDF receipt
* JSON metadata
* Secure tokenized public receipt URL

Example:

```bash
https://moelinvo.streamlit.app/?token=YOUR_TOKEN
```


## 🎨 Brand Configuration

`brand_config.json`

```json
{
  "brand": {
    "tagline": "Your Brand Tagline",
    "phone": "+62...",
    "email": "youremail@email.com",
    "sosmed": "@sosmed"
  },
  "payment": {
    "bank": "Bank Name",
    "rekening": "123456789",
    "atasNama": "a/n Your Name",
    "alternative": ""
  },
  "signature": {
    "mode": "image",
    "script": "Sign Script~",
    "image": "signature.png",
    "fullName": "Your Full Name",
    "role": "Your Services"
  }
}
```


## 📜 License

MIT License


## 👨‍💻 Author
**Maulana Ihsan Ahmad**\
*MOELDSGN Graphic Design Services*\
Instagram: @moeldsgn
