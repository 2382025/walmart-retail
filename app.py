import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ==========================================
# 1. PENGATURAN HALAMAN
# ==========================================

st.set_page_config(
    page_title="Walmart Retail BI",
    page_icon="📊",
    layout="wide"
)

# ==========================================
# 2. MEMUAT DATA
# ==========================================

@st.cache_data
def load_data():
    df = pd.read_csv("Walmart_Cleaned.csv")

    # File hasil pembersihan menggunakan format tanggal YYYY-MM-DD.
    # Baris ini juga tetap dapat membaca format tanggal lain.
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    df = df.dropna(subset=["Date", "Weekly_Sales", "Store"])

    # Memastikan kolom numerik terbaca sebagai angka
    numeric_columns = [
        "Store", "Weekly_Sales", "Holiday_Flag",
        "Temperature", "Fuel_Price", "CPI", "Unemployment"
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["Store", "Weekly_Sales"])
    df["Store"] = df["Store"].astype(int)

    return df.sort_values("Date")


df = load_data()

if df.empty:
    st.error("Data tidak ditemukan atau tidak memiliki baris yang dapat digunakan.")
    st.stop()

# ==========================================
# 3. PENYARINGAN DATA
# ==========================================

st.sidebar.title("📊 Walmart Retail BI")
st.sidebar.caption("Dasbor Analisis Penjualan Walmart")
st.sidebar.divider()

tanggal_awal = df["Date"].min().date()
tanggal_akhir = df["Date"].max().date()

rentang_tanggal = st.sidebar.date_input(
    "Pilih Rentang Tanggal",
    value=(tanggal_awal, tanggal_akhir),
    min_value=tanggal_awal,
    max_value=tanggal_akhir
)

semua_toko = sorted(df["Store"].dropna().unique())

toko_dipilih = st.sidebar.multiselect(
    "Pilih Toko",
    options=semua_toko,
    default=semua_toko
)

if not toko_dipilih:
    st.warning("Silakan pilih setidaknya satu toko pada bagian penyaringan.")
    st.stop()

if isinstance(rentang_tanggal, (tuple, list)) and len(rentang_tanggal) == 2:
    tanggal_mulai, tanggal_selesai = rentang_tanggal
else:
    tanggal_mulai = tanggal_awal
    tanggal_selesai = tanggal_akhir

data = df[
    (df["Date"].dt.date >= tanggal_mulai) &
    (df["Date"].dt.date <= tanggal_selesai) &
    (df["Store"].isin(toko_dipilih))
].copy()

if data.empty:
    st.warning("Tidak ada data untuk pilihan penyaringan tersebut. Silakan ubah penyaringan.")
    st.stop()
