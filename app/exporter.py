# app/exporter.py
import pandas as pd
import fpdf
from datetime import datetime
import base64
import streamlit as st

def export_to_excel(messages, filename=None):
    df = pd.DataFrame([
        {"Role": m["role"], "Content": m["content"]}
        for m in messages
    ])
    filename = filename or f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    df.to_excel(f"exports/{filename}", index=False)
    return filename

def export_to_pdf(messages, filename=None):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for m in messages:
        pdf.cell(0, 10, f"{m['role'].title()}: ", ln=True, align='L')
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 8, m["content"])
        pdf.ln(2)
        pdf.set_font("Arial", size=12)
    filename = filename or f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    pdf.output(f"exports/{filename}")
    return filename

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{os.path.basename(bin_file)}">📥 Download {file_label}</a>'
    return href