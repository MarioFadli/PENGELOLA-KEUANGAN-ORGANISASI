import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIG HALAMAN ---
st.set_page_config(
    page_title="Keuangan Organisasi Pro",
    page_icon="💸",
    layout="wide"
)

APP_AUTHOR = "Mario Fadli"

# --- KONEKSI DATABASE CLOUD ---
# Masukkan URI Supabase milikmu di sini atau lewat Streamlit Secrets
# UBAH BARIS 20 MENJADI SEPERTI INI:
DATABASE_URL = "postgresql://postgres.lsmwcepfecddleswxhfl:10Mei2006%2310@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

@st.cache_resource
def get_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            amount DOUBLE PRECISION NOT NULL,
            type VARCHAR(20) NOT NULL,
            category VARCHAR(50) NOT NULL,
            payment_method VARCHAR(50) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()

try:
    init_db()
except Exception as e:
    st.error(f"Gagal terhubung ke database. Pastikan URI database sudah benar. Error: {e}")

# --- HELPER FUNCTIONS ---
def get_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY id DESC", conn)
    return df

def insert_data(amount, trans_type, category, payment_method, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (amount, type, category, payment_method, description)
        VALUES (%s, %s, %s, %s, %s)
    """, (amount, trans_type, category, payment_method, description))
    conn.commit()
    cursor.close()

# --- HEADER & IDENTITAS ---
st.title("💸 Pengelola Keuangan Organisasi")
st.caption(f"Sistem Informasi Rekap Keuangan Real-Time | Developed by **{APP_AUTHOR}**")

# --- LOGIN SIMPEL (ROLE MANAGEMENT) ---
st.sidebar.header("🔐 Akses Pengguna")
role = st.sidebar.radio("Masuk Sebagai:", ["Anggota (Lihat Laporan)", "Pengurus/Bendahara (Input Data)"])

passkey = ""
if role == "Pengurus/Bendahara (Input Data)":
    passkey = st.sidebar.text_input("Masukkan PIN Bendahara:", type="password")

# --- DASHBOARD METRIK SALDO ---
df = get_data()

total_in = df[df['type'] == 'pemasukan']['amount'].sum() if not df.empty else 0.0
total_out = df[df['type'] == 'pengeluaran']['amount'].sum() if not df.empty else 0.0
saldo = total_in - total_out

col1, col2, col3 = st.columns(3)
col1.metric("💰 Saldo Saat Ini", f"Rp {saldo:,.0f}")
col2.metric("🟢 Total Pemasukan", f"Rp {total_in:,.0f}")
col3.metric("🔴 Total Pengeluaran", f"Rp {total_out:,.0f}")

st.divider()

# --- TAB NAVIGASI ---
tab_riwayat, tab_input, tab_grafik = st.tabs(["📜 Riwayat & Rekap", "➕ Input Transaksi", "📊 Grafik & Export"])

# TAB 1: RIWAYAT
with tab_riwayat:
    st.subheader("Data Transaksi Organisasi")
    if not df.empty:
        search = st.text_input("🔍 Cari transaksi...")
        if search:
            filtered_df = df[
                df['description'].str.contains(search, case=False, na=False) |
                df['category'].str.contains(search, case=False, na=False)
            ]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Belum ada data transaksi tersimpan.")

# TAB 2: INPUT (KHUSUS BENDAHARA)
with tab_input:
    st.subheader("Form Input Transaksi Baru")
    
    # Ganti "1234" dengan PIN yang kamu inginkan
    if role == "Pengurus/Bendahara (Input Data)" and passkey == "1234":
        with st.form("form_transaksi", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            trans_type = col_a.selectbox("Tipe Transaksi", ["pengeluaran", "pemasukan"])
            amount = col_b.number_input("Nominal (Rp)", min_value=1000, step=5000)
            
            cats = ["Makan/Konsumsi", "Acara/Kegiatan", "Logistik/Perlengkapan", "Sewa Tempat", "Gaji/Honor", "Lain-lain"] if trans_type == "pengeluaran" else ["Iuran Anggota", "Sponsor/Donasi", "Dana Usaha", "Lain-lain"]
            category = col_a.selectbox("Kategori", cats)
            payment_method = col_b.selectbox("Metode Pembayaran", ["Cash", "Transfer Bank", "QRIS", "E-Wallet"])
            
            description = st.text_area("Keterangan / Keperluan")
            
            submitted = st.form_submit_button("💾 Simpan Transaksi")
            if submitted:
                insert_data(amount, trans_type, category, payment_method, description)
                st.success("Transaksi berhasil disimpan!")
                st.rerun()
    else:
        st.warning("🔒 Masukkan PIN Bendahara yang benar di sidebar untuk mengakses form input.")

# TAB 3: GRAFIK & EXPORT
with tab_grafik:
    st.subheader("Analisis Pengeluaran & Pemasukan")
    
    if not df.empty:
        chart_type = st.radio("Tampilkan Grafik Untuk:", ["pengeluaran", "pemasukan"], horizontal=True)
        df_chart = df[df['type'] == chart_type]
        
        if not df_chart.empty:
            cat_summary = df_chart.groupby("category")["amount"].sum()
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.pie(cat_summary, labels=cat_summary.index, autopct='%1.1f%%', startangle=90)
            ax.set_title(f"Distribusi {chart_type.capitalize()}")
            st.pyplot(fig)
        else:
            st.info(f"Belum ada data {chart_type}.")

        st.divider()
        st.subheader("📥 Export Laporan")
        
        # Export Excel
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Keuangan')
        st.download_button(
            label="📊 Download Laporan Excel",
            data=output_excel.getvalue(),
            file_name=f"laporan_keuangan_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )