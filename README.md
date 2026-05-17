# MOELDSGN Streamlit Invoice

Struktur project:

```text
streamlit-invoice/
├── .venv/
├── app.py
├── style.css
├── invoice/
│   ├── index.json
│   └── invoice-001.json
├── assets/
├── requirements-streamlit.txt
└── README.md
```

## Jalankan di Mac

```bash
cd ~/Downloads/streamlit-invoice
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-streamlit.txt
streamlit run app.py
```

## Export PDF

Klik tombol **Export PDF / Print** di preview invoice, lalu pilih **Save as PDF** dari dialog print browser.
