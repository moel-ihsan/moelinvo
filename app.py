import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import tempfile
from playwright.sync_api import sync_playwright
from jinja2 import Environment, FileSystemLoader, select_autoescape
import base64
import secrets
import shutil

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io


BASE_DIR = Path(__file__).parent
CSS_PATH = BASE_DIR / "style.css"

TEMPLATE_DIR = BASE_DIR / "templates"

INVOICE_DIR = BASE_DIR / "invoice"
INDEX_PATH = INVOICE_DIR / "index.json"
JSON_DIR = INVOICE_DIR / "json"
PDF_DIR = INVOICE_DIR / "pdf"

CONFIG_DIR = BASE_DIR / "config"
BRAND_CONFIG_PATH = CONFIG_DIR / "brand_config.json"
RECEIPT_DIR = INVOICE_DIR / "receipts"

st.set_page_config(page_title="MOELDSGN Invoice", page_icon="🧾", layout="wide")

SCOPES = ["https://www.googleapis.com/auth/drive"]


@st.cache_resource
def get_drive_service():
    creds = Credentials.from_authorized_user_info(
        dict(st.secrets["google_oauth_token"]),
        SCOPES
    )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("drive", "v3", credentials=creds)


get_drive_service()

def upload_bytes_to_drive(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    folder_id: str,
):
    service = get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype=mime_type,
        resumable=False,
    )

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name,webViewLink",
        supportsAllDrives=True,
    ).execute()

    return uploaded


def find_drive_file(filename: str, folder_id: str):
    service = get_drive_service()

    query = (
        f"name='{filename}' "
        f"and '{folder_id}' in parents "
        f"and trashed=false"
    )

    response = service.files().list(
        q=query,
        fields="files(id,name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    files = response.get("files", [])

    if not files:
        return None

    return files[0]


def download_drive_file(file_id: str):
    service = get_drive_service()

    request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()

    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue()


def download_drive_file_by_name(filename: str, folder_id: str) -> bytes | None:
    file = find_drive_file(filename, folder_id)

    if not file:
        return None

    return download_drive_file(file["id"])


def generate_token() -> str:
    return secrets.token_urlsafe(16)


def save_receipt_metadata_drive(invoice_no: str, token: str) -> dict:
    receipt_folder_id = st.secrets["GOOGLE_DRIVE_RECEIPT_FOLDER_ID"]

    receipt_data = {
        "token": token,
        "invoice_no": invoice_no,
        "json_filename": safe_invoice_filename(invoice_no, "json"),
        "pdf_filename": safe_invoice_filename(invoice_no, "pdf"),
    }

    receipt_bytes = json.dumps(
        receipt_data,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    uploaded = upload_bytes_to_drive(
        file_bytes=receipt_bytes,
        filename=f"{token}.json",
        mime_type="application/json",
        folder_id=receipt_folder_id,
    )

    return uploaded


def load_receipt_by_token_drive(token: str) -> dict | None:
    receipt_folder_id = st.secrets["GOOGLE_DRIVE_RECEIPT_FOLDER_ID"]

    data_bytes = download_drive_file_by_name(
        filename=f"{token}.json",
        folder_id=receipt_folder_id,
    )

    if data_bytes is None:
        return None

    try:
        return json.loads(data_bytes.decode("utf-8"))
    except Exception:
        return None
    

def generate_pdf_from_html(html_content: str, output_path: str):

    chromium_path = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
        or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        or "/Applications/Chromium.app/Contents/MacOS/Chromium"
    )

    if not Path(chromium_path).exists():
        raise RuntimeError("Chromium / Google Chrome browser not found.")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chromium_path,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")

        page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
        )

        browser.close()


def load_css() -> str:
    if CSS_PATH.exists():
        return CSS_PATH.read_text(encoding="utf-8")
    return ""


def rupiah(amount: int) -> str:
    return "IDR " + f"{int(amount):,}".replace(",", ".")

def get_latest_invoice_file() -> Path | None:
    if INDEX_PATH.exists():
        try:
            index_data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            files = index_data.get("files", [])
            invoice_files = [f for f in files if f.startswith("invoice-") and f.endswith(".json")]
            if invoice_files:
                latest = sorted(invoice_files)[-1]
                latest_path = INVOICE_DIR / latest
                if latest_path.exists():
                    return latest_path
        except Exception:
            pass

    files = sorted(JSON_DIR.glob("*.json"))
    return files[-1] if files else None


def load_default_invoice() -> dict:
    latest_path = get_latest_invoice_file()
    if latest_path and latest_path.exists():
        try:
            return json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "invoice": {"number": "MOEL-INV-001", "date": "17 May 2026", "dueDate": "24 May 2026"},
        "client": {"name": "Nama Client", "program": "Website / Graphic Design"},
        "items": [
            {"description": "Pembuatan Website", "detail": "Project website company profile", "qty": 1, "price": 3500000, "link": ""},
            {"description": "Termin Pembayaran Kedua", "detail": "Pembayaran lanjutan setelah uang muka", "qty": 1, "price": 500000, "link": ""},
        ],
        "pricing": {"discount": 0},
        "notes": [
            "Prices apply to digital design services only.", 
            "Printing services are not included.",
            "All design files are delivered digitally via Canva links.",
            "Each product item represents a specific design output."
        ],
    }


def load_brand_config() -> dict:
    default_config = {
        "brand": {
            "tagline": "Graphic Design Services",
            "phone": "wa.me/6281234567890",
            "email": "moeldsgn@gmail.com",
            "sosmed": "@moeldsgn",
        },
        "payment": {
            "bank": "BCA / BRI",
            "rekening": "1234 5678 901",
            "atasNama": "a/n Moel Design",
            "alternative": "GoPay / OVO / Dana\n0812-3456-7890",
        },
        "signature": {
            "mode": "script",
            "script": "Moeldsgn~",
            "image": "assets/signature/signature.png",
            "fullName": "MOELDSGN",
            "role": "Graphic Design Services",
        },
    }

    if BRAND_CONFIG_PATH.exists():
        try:
            return json.loads(BRAND_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    BRAND_CONFIG_PATH.write_text(
        json.dumps(default_config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return default_config

def render_invoice(data: dict, css: str) -> str:
    original_total = sum(int(item["qty"]) * int(item["price"]) for item in data["items"])
    discount = int(data.get("discount", 0))
    after_discount = original_total - discount
    tax_rate = float(data.get("tax_rate", 0))
    tax_amount = round(after_discount * tax_rate)
    final_total = after_discount + tax_amount

    rendered_items = []
    for idx, item in enumerate(data["items"], start=1):
        qty = int(item["qty"])
        price = int(item["price"])
        subtotal = qty * price

        rendered_items.append({
            "no": idx,
            "description": item.get("description", ""),
            "detail": item.get("detail", ""),
            "link": item.get("link", ""),
            "qty": qty,
            "price": rupiah(price),
            "subtotal": rupiah(subtotal),
        })

    tax_text = f"{rupiah(tax_amount)} ({tax_rate * 100:.0f}%)" if tax_rate > 0 else "IDR 0"

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    sig = dict(data["signature"])
    if sig.get("mode") == "image" and sig.get("image"):
        image_path = BASE_DIR / sig["image"]

        if image_path.exists():
            ext = image_path.suffix.lower().replace(".", "")
            mime = "jpeg" if ext in ["jpg", "jpeg"] else ext

            img_bytes = image_path.read_bytes()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            sig["image"] = f"data:image/{mime};base64,{img_b64}"
        else:
            sig["mode"] = "script"

    template = env.get_template("invoice_template.html")

    return template.render(
        css=css,
        brand=data["brand"],
        payment=data["payment"],
        signature=sig,
        invoice=data["invoice"],
        client=data["client"],
        items=rendered_items,
        notes=data.get("notes", []),
        original_total=rupiah(original_total),
        discount=rupiah(discount),
        tax_text=tax_text,
        final_total=rupiah(final_total),
    )


def build_invoice_json(data: dict) -> str:
    export_data = {
        "brand": data["brand"],
        "payment": data["payment"],
        "signature": data["signature"],
        "invoice": data["invoice"],
        "client": data["client"],
        "items": data["items"],
        "pricing": {"discount": data.get("discount", 0)},
        "tax_rate": data.get("tax_rate", 0),
        "notes": data.get("notes", []),
    }
    return json.dumps(export_data, ensure_ascii=False, indent=2)


css = load_css()
default_invoice = load_default_invoice()
brand_config = load_brand_config()

token = st.query_params.get("token")

if token:
    receipt = load_receipt_by_token_drive(token)

    if receipt is None:
        st.error("Receipt tidak ditemukan atau token tidak valid.")
        st.stop()

    invoice_no = receipt["invoice_no"]
    json_filename = receipt["json_filename"]
    pdf_filename = receipt["pdf_filename"]

    json_bytes = download_drive_file_by_name(
        filename=json_filename,
        folder_id=st.secrets["GOOGLE_DRIVE_JSON_FOLDER_ID"],
    )

    pdf_bytes = download_drive_file_by_name(
        filename=pdf_filename,
        folder_id=st.secrets["GOOGLE_DRIVE_PDF_FOLDER_ID"],
    )

    st.title("🧾 Receipt")
    st.write(f"Invoice No: `{invoice_no}`")

    if pdf_bytes:
        st.download_button(
            "Download Receipt PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
        )
    else:
        st.error("File PDF tidak ditemukan di Google Drive.")

    if json_bytes:
        invoice_json = json.loads(json_bytes.decode("utf-8"))

        preview_data = {
            **invoice_json,
            "discount": invoice_json.get("pricing", {}).get("discount", 0),
            "tax_rate": invoice_json.get("tax_rate", 0),
        }

        receipt_html = render_invoice(preview_data, css)
        components.html(receipt_html, height=1200, scrolling=True)

        st.success("Receipt valid. Silakan download PDF invoice.")
    else:
        st.warning("Preview invoice tidak tersedia karena file JSON tidak ditemukan.")

    st.stop()


admin_email = st.secrets["ADMIN_EMAIL"]

user = st.user.to_dict()
is_logged_in = user.get("is_logged_in", False)

if not is_logged_in:
    st.title("🔐 MOELINVO Admin")
    st.warning("Admin area. Silakan login terlebih dahulu.")

    if st.button("Login with Google"):
        st.login()

    st.stop()

if user.get("email") != admin_email:
    st.error("Akses ditolak. Halaman ini hanya untuk admin.")

    if st.button("Logout"):
        st.logout()

    st.stop()

with st.sidebar:
    st.caption(f"Admin: {user.get('email')}")

    if st.button("Logout"):
        st.logout()


st.title("🧾 MOELDSGN Invoice Generator")

with st.sidebar:
    st.header("Brand")
    brand_tagline = st.text_input("Tagline", brand_config["brand"]["tagline"])
    brand_phone = st.text_input("Phone / WA", brand_config["brand"]["phone"])
    brand_email = st.text_input("Email", brand_config["brand"]["email"])
    brand_sosmed = st.text_input("Sosmed", brand_config["brand"]["sosmed"])

    st.header("Payment")
    bank = st.text_input("Bank", brand_config["payment"]["bank"])
    rekening = st.text_input("No. Rekening", brand_config["payment"]["rekening"])
    atas_nama = st.text_input("Atas Nama", brand_config["payment"]["atasNama"])
    pay_alt = st.text_area("Alternatif", brand_config["payment"]["alternative"])

    st.header("Signature")
    sig_mode = st.selectbox(
        "Mode Tanda Tangan",
        ["script", "image"],
        index=0 if brand_config["signature"].get("mode", "script") == "script" else 1,
    )

    sig_script = st.text_input("Script", brand_config["signature"].get("script", "Moeldsgn~"))
    sig_image = st.text_input("Image Path", brand_config["signature"].get("image", "assets/signature/signature.png"))
    sig_name = st.text_input("Nama", brand_config["signature"]["fullName"])
    sig_role = st.text_input("Role", brand_config["signature"]["role"])

col1, col2 = st.columns(2)
with col1:
    invoice_no = st.text_input("Invoice No", default_invoice.get("invoice", {}).get("number", "MOEL-INV-001"))
    invoice_date = st.date_input("Invoice Date", date.today())
    due_date = st.date_input("Due Date", date.today() + timedelta(days=7))
with col2:
    client_name = st.text_input("Client Name", default_invoice.get("client", {}).get("name", "Nama Client"))
    client_program = st.text_input("Program / Project", default_invoice.get("client", {}).get("program", "Website / Graphic Design"))
    tax_rate = st.number_input("PPN / Tax Rate", min_value=0.0, max_value=1.0, value=0.0, step=0.01)

st.subheader("Items")
default_items = default_invoice.get("items", []) or []
item_count = st.number_input("Jumlah item", min_value=1, max_value=20, value=max(1, len(default_items)), step=1)

items = []
for i in range(item_count):
    fallback = default_items[i] if i < len(default_items) else {"description": "", "detail": "", "qty": 1, "price": 0, "link": ""}
    with st.expander(f"Item {i + 1}", expanded=i < 3):
        c1, c2, c3 = st.columns([3, 1, 2])
        desc = c1.text_input("Deskripsi", fallback.get("description", ""), key=f"desc_{i}")
        qty = c2.number_input("Qty", min_value=1, value=int(fallback.get("qty", 1)), key=f"qty_{i}")
        price = c3.number_input("Harga", min_value=0, value=int(fallback.get("price", 0)), step=50000, key=f"price_{i}")
        detail = st.text_input("Detail", fallback.get("detail", ""), key=f"detail_{i}")
        link = st.text_input("Link File", fallback.get("link", ""), key=f"link_{i}")
        items.append({"description": desc, "qty": qty, "price": price, "detail": detail, "link": link})

discount = st.number_input("Discount", min_value=0, value=int(default_invoice.get("pricing", {}).get("discount", 0)), step=50000)
notes_raw = st.text_area("Notes", "\n".join(default_invoice.get("notes", [])))
notes = [line.strip() for line in notes_raw.splitlines() if line.strip()]

invoice_data = {
    "brand": {
        "tagline": brand_tagline,
        "phone": brand_phone,
        "email": brand_email,
        "sosmed": brand_sosmed,
    },
    "payment": {
        "bank": bank,
        "rekening": rekening,
        "atasNama": atas_nama,
        "alternative": pay_alt,
    },
    "signature": {
        "mode": sig_mode,
        "script": sig_script,
        "image": sig_image,
        "fullName": sig_name,
        "role": sig_role,
    },
    "invoice": {
        "number": invoice_no,
        "date": invoice_date.strftime("%d %B %Y"),
        "dueDate": due_date.strftime("%d %B %Y"),
    },
    "client": {
        "name": client_name,
        "program": client_program,
    },
    "items": items,
    "discount": discount,
    "tax_rate": tax_rate,
    "notes": notes,
}

def safe_invoice_filename(invoice_no: str, ext: str) -> str:
    safe_name = (
        invoice_no
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "-")
    )
    return f"{safe_name}.{ext}"

def invoice_no_exists_drive(invoice_no: str) -> bool:
    json_folder_id = st.secrets["GOOGLE_DRIVE_JSON_FOLDER_ID"]
    pdf_folder_id = st.secrets["GOOGLE_DRIVE_PDF_FOLDER_ID"]

    json_filename = safe_invoice_filename(invoice_no, "json")
    pdf_filename = safe_invoice_filename(invoice_no, "pdf")

    return (
        find_drive_file(json_filename, json_folder_id) is not None
        or find_drive_file(pdf_filename, pdf_folder_id) is not None
    )


def delete_drive_file(file_id: str):
    service = get_drive_service()

    service.files().delete(
        fileId=file_id,
        supportsAllDrives=True,
    ).execute()


def delete_drive_file_by_name(filename: str, folder_id: str):
    file = find_drive_file(filename, folder_id)

    if file:
        delete_drive_file(file["id"])


def save_invoice_files_drive(
    invoice_no: str,
    json_text: str,
    pdf_bytes: bytes,
    overwrite: bool = False,
) -> dict:
    json_folder_id = st.secrets["GOOGLE_DRIVE_JSON_FOLDER_ID"]
    pdf_folder_id = st.secrets["GOOGLE_DRIVE_PDF_FOLDER_ID"]

    json_filename = safe_invoice_filename(invoice_no, "json")
    pdf_filename = safe_invoice_filename(invoice_no, "pdf")

    if not overwrite:
        if invoice_no_exists_drive(invoice_no):
            raise FileExistsError(f"Invoice {invoice_no} sudah ada.")

    if overwrite:
        delete_drive_file_by_name(json_filename, json_folder_id)
        delete_drive_file_by_name(pdf_filename, pdf_folder_id)

    json_uploaded = upload_bytes_to_drive(
        file_bytes=json_text.encode("utf-8"),
        filename=json_filename,
        mime_type="application/json",
        folder_id=json_folder_id,
    )

    pdf_uploaded = upload_bytes_to_drive(
        file_bytes=pdf_bytes,
        filename=pdf_filename,
        mime_type="application/pdf",
        folder_id=pdf_folder_id,
    )

    return {
        "json": json_uploaded,
        "pdf": pdf_uploaded,
        "json_filename": json_filename,
        "pdf_filename": pdf_filename,
    }

html_doc = render_invoice(invoice_data, css)

with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
    generate_pdf_from_html(html_doc, tmp_pdf.name)
    pdf_bytes = Path(tmp_pdf.name).read_bytes()

components.html(html_doc, height=1200, scrolling=True)

json_text = build_invoice_json(invoice_data)
is_duplicate = invoice_no_exists_drive(invoice_no)

overwrite_existing = False

if is_duplicate:
    st.warning(
        f"Invoice No `{invoice_no}` sudah ada."
    )

    overwrite_existing = st.checkbox(
        "Override invoice lama",
        value=False,
    )

save_disabled = is_duplicate and not overwrite_existing

if st.button("Save Invoice PDF + JSON", disabled=save_disabled):

    saved_files = save_invoice_files_drive(
        invoice_no=invoice_no,
        json_text=json_text,
        pdf_bytes=pdf_bytes,
        overwrite=overwrite_existing,
    )

    token = generate_token()
    receipt_file = save_receipt_metadata_drive(invoice_no, token)

    APP_URL = "https://moelinvo.streamlit.app"
    receipt_link = f"{APP_URL}?token={token}"

    if overwrite_existing:
        st.success("Invoice lama berhasil dioverride.")
    else:
        st.success("Invoice berhasil disimpan.")

    st.write(f"Token: `{token}`")
    st.write(f"Receipt metadata: `{receipt_file['name']}`")
    st.code(receipt_link)