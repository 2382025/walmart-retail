"""
Walmart Business Intelligence - Decision Support Dashboard
==========================================================
Jalankan:  streamlit run app.py
Data    :  Walmart_Cleaned.csv (letakkan satu folder dengan app.py) atau unggah lewat sidebar.

Struktur aplikasi
  1. Ringkasan Eksekutif   -> KPI & tren penjualan
  2. Analisis Toko         -> Pareto/ABC, pertumbuhan, volatilitas
  3. Musiman & Hari Libur  -> indeks bulanan, dampak hari libur, pekan puncak
  4. Faktor Eksternal      -> suhu, BBM, CPI, pengangguran
  5. Pusat Keputusan       -> rekomendasi keputusan berbasis data + simulasi what-if
"""

import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# KONFIGURASI
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Walmart BI - Decision Support",
    page_icon="🛒",
    layout="wide",
)

BLUE, YELLOW, DARK = "#0071CE", "#FFC220", "#041E42"
RED, GREEN, GREY = "#D64545", "#2E9E5B", "#9AA5B1"
CLASS_COLOR = {"A": BLUE, "B": YELLOW, "C": GREY}
MONTH_ID = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
            7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"}
HOLIDAY_NAMES = {2: "Super Bowl", 9: "Labor Day", 11: "Thanksgiving",
                 12: "Natal / Akhir Tahun (pekan 30-31 Des)"}
REQUIRED = ["Store", "Date", "Weekly_Sales", "Holiday_Flag", "Temperature",
            "Fuel_Price", "CPI", "Unemployment"]
DEFAULT_FILE = "Walmart_Cleaned.csv"

st.markdown(
    f"""
    <style>
    .hero {{background: linear-gradient(90deg, {DARK}, {BLUE}); padding: 1.2rem 1.5rem;
            border-radius: 12px; color: white; margin-bottom: 1rem;}}
    .hero h1 {{color: white; margin: 0; font-size: 1.8rem;}}
    .hero p {{color: #dce9f7; margin: .3rem 0 0 0;}}
    </style>
    <div class="hero">
      <h1>🛒 Walmart Business Intelligence</h1>
      <p>Dashboard pendukung pengambilan keputusan (Decision Making) berbasis data penjualan mingguan</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# HELPER TAMPILAN (kompatibel dengan versi Streamlit lama & baru)
# ----------------------------------------------------------------------------
def show(fig, height=420):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def table(df, **kwargs):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def fmt_usd(x, d=1):
    if x is None or pd.isna(x):
        return "-"
    ax = abs(x)
    if ax >= 1e9:
        return f"${x / 1e9:,.{d}f}B"
    if ax >= 1e6:
        return f"${x / 1e6:,.{d}f}M"
    if ax >= 1e3:
        return f"${x / 1e3:,.0f}K"
    return f"${x:,.0f}"


def pct(x, d=1, sign=True):
    if x is None or pd.isna(x):
        return "-"
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


# ----------------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(src):
    df = pd.read_csv(src)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {', '.join(missing)}")
    df["Date"] = pd.to_datetime(df["Date"])
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
    return df.sort_values(["Store", "Date"]).reset_index(drop=True)


# ----------------------------------------------------------------------------
# FUNGSI ANALISIS (semua murni pandas, mudah diuji)
# ----------------------------------------------------------------------------
def weekly_table(df):
    """Agregasi per pekan: rata-rata per toko, total jaringan, dan flag libur."""
    w = (df.groupby("Date")
           .agg(Sales=("Weekly_Sales", "mean"),
                Total=("Weekly_Sales", "sum"),
                Holiday=("Holiday_Flag", "max"))
           .reset_index())
    w["Year"] = w["Date"].dt.year
    w["Week"] = w["Date"].dt.isocalendar().week.astype(int)
    return w


def store_summary(df):
    """Ringkasan per toko + klasifikasi ABC (Pareto 70% / 90%)."""
    g = (df.groupby("Store").Weekly_Sales
           .agg(Total="sum", Rata2="mean", Std="std").reset_index())
    g["CV"] = g["Std"] / g["Rata2"]
    g = g.sort_values("Total", ascending=False).reset_index(drop=True)
    g["Share"] = g["Total"] / g["Total"].sum()
    g["CumShare"] = g["Share"].cumsum()
    prev = g["CumShare"] - g["Share"]
    g["Kelas"] = np.select([prev < 0.70, prev < 0.90], ["A", "B"], "C")
    return g


def store_growth(df):
    """
    Pertumbuhan per toko pada periode yang sebanding (Feb-Okt) karena data
    2010 mulai Februari dan data 2012 berakhir Oktober.
    """
    core = df[df["Month"].between(2, 10)]
    p = core.pivot_table(index="Store", columns="Year",
                         values="Weekly_Sales", aggfunc="mean")
    ys = sorted(p.columns.tolist())
    out = pd.DataFrame({"Store": p.index})
    out["Rata_Terakhir"] = p[ys[-1]].values if len(ys) >= 1 else np.nan
    out["Rata_Sebelum"] = p[ys[-2]].values if len(ys) >= 2 else np.nan
    out["G_last"] = out["Rata_Terakhir"] / out["Rata_Sebelum"] - 1
    if len(ys) >= 3:
        out["G_prev"] = p[ys[-2]].values / p[ys[-3]].values - 1
    else:
        out["G_prev"] = np.nan
    out.attrs["years"] = ys
    return out


def overall_growth(df):
    core = df[df["Month"].between(2, 10)]
    m = core.groupby("Year").Weekly_Sales.mean().sort_index()
    if len(m) < 2:
        return np.nan, m.index.tolist()
    return m.iloc[-1] / m.iloc[-2] - 1, m.index.tolist()


def seasonality(df):
    """Indeks musiman: rata-rata penjualan bulan tsb / rata-rata keseluruhan - 1."""
    m = df.groupby("Month").Weekly_Sales.mean()
    return m / df.Weekly_Sales.mean() - 1


def holiday_events(df):
    """Dampak tiap pekan libur dibanding pekan non-libur (global & lokal ±4 pekan)."""
    w = weekly_table(df)
    nonhol = w[w.Holiday == 0]
    base_g = nonhol.Sales.mean()
    rows = []
    for _, r in w[w.Holiday == 1].iterrows():
        win = nonhol[(nonhol.Date >= r.Date - pd.Timedelta(days=28)) &
                     (nonhol.Date <= r.Date + pd.Timedelta(days=28))]
        base_l = win.Sales.mean() if len(win) else np.nan
        rows.append(dict(
            Date=r.Date,
            Event=HOLIDAY_NAMES.get(r.Date.month, "Libur lain"),
            Sales=r.Sales,
            Lift_Global=r.Sales / base_g - 1,
            Lift_Local=r.Sales / base_l - 1 if pd.notna(base_l) else np.nan,
        ))
    return pd.DataFrame(rows, columns=["Date", "Event", "Sales", "Lift_Global", "Lift_Local"])


def holiday_summary(ev):
    if ev.empty:
        return pd.DataFrame(columns=["Event", "Rata2_Toko", "Lift_Global", "Lift_Local", "N"])
    return (ev.groupby("Event")
              .agg(Rata2_Toko=("Sales", "mean"), Lift_Global=("Lift_Global", "mean"),
                   Lift_Local=("Lift_Local", "mean"), N=("Date", "count"))
              .reset_index().sort_values("Lift_Global", ascending=False))


def driver_table(df):
    d = df.copy()
    d["Indeks"] = d["Weekly_Sales"] / d.groupby("Store")["Weekly_Sales"].transform("mean")
    cols = ["Temperature", "Fuel_Price", "CPI", "Unemployment"]
    return pd.DataFrame({
        "Faktor": cols,
        "Korelasi dgn Penjualan": [d["Weekly_Sales"].corr(d[c]) for c in cols],
        "Korelasi dgn Indeks Toko": [d["Indeks"].corr(d[c]) for c in cols],
    }), d


def variance_explained(df):
    """R² dari (a) identitas toko terhadap penjualan, (b) pekan-dalam-tahun terhadap indeks toko."""
    y = df["Weekly_Sales"]
    sst = ((y - y.mean()) ** 2).sum()
    store_mean = df.groupby("Store")["Weekly_Sales"].transform("mean")
    r2_store = 1 - ((y - store_mean) ** 2).sum() / sst if sst > 0 else np.nan
    idx = y / store_mean
    wk_mean = idx.groupby(df["Week"]).transform("mean")
    sst_i = ((idx - idx.mean()) ** 2).sum()
    r2_week = 1 - ((idx - wk_mean) ** 2).sum() / sst_i if sst_i > 0 else np.nan
    return r2_store, r2_week


def fmt_date(d):
    return f"{d.day} {MONTH_ID[d.month]} {d.year}"


def store_actions(ss, gr):
    """Rekomendasi tindakan per toko = kelas ABC x pertumbuhan terakhir."""
    m = ss.merge(gr[["Store", "G_last", "G_prev"]], on="Store", how="left")

    def act(r):
        g = r["G_last"]
        if pd.isna(g):
            return "⚪ Monitor"
        if r["Kelas"] == "A" and g < 0:
            return "🔴 Selamatkan - audit penyebab penurunan"
        if r["Kelas"] == "A":
            return "🟢 Pertahankan - prioritas stok & layanan"
        if g >= 0.03:
            return "🔵 Kembangkan - tambah stok/ruang & promo"
        if r["Kelas"] == "B" and g < 0:
            return "🟠 Perbaiki - tinjau assortment & promo lokal"
        if r["Kelas"] == "C" and g < 0:
            return "🟠 Evaluasi efisiensi biaya"
        return "⚪ Monitor"

    m["Rekomendasi"] = m.apply(act, axis=1)
    return m


def store_list(gr, n=5, ascending=True, ss=None):
    t = gr.dropna(subset=["G_last"]).sort_values("G_last", ascending=ascending).head(n)
    parts = []
    for _, r in t.iterrows():
        extra = ""
        if ss is not None:
            k = ss.loc[ss.Store == r.Store, "Kelas"]
            extra = f", kelas {k.iloc[0]}" if len(k) else ""
        parts.append(f"Toko {int(r.Store)} ({pct(r.G_last)}{extra})")
    return "; ".join(parts)


# ----------------------------------------------------------------------------
# MESIN KEPUTUSAN
# ----------------------------------------------------------------------------
def build_decisions(df):
    ss, gr = store_summary(df), store_growth(df)
    ev = holiday_events(df)
    hs = holiday_summary(ev)
    si = seasonality(df)
    w = weekly_table(df)
    drv, _ = driver_table(df)
    ys = gr.attrs.get("years", [])
    y_last, y_prev = (ys[-1], ys[-2]) if len(ys) >= 2 else ("?", "?")
    D = []

    def hs_val(name, col):
        r = hs[hs.Event == name]
        return r[col].iloc[0] if len(r) else np.nan

    # 1 --- Thanksgiving
    tg_lift, tg_loc = hs_val("Thanksgiving", "Lift_Global"), hs_val("Thanksgiving", "Lift_Local")
    tg_sales = hs_val("Thanksgiving", "Rata2_Toko")
    if pd.notna(tg_lift):
        D.append(dict(
            prio="Tinggi", area="Inventori & Tenaga Kerja",
            keputusan="Jadikan Thanksgiving sebagai pekan prioritas utama: naikkan stok dan jam kerja sebelum pekan tsb.",
            bukti=(f"Pekan Thanksgiving rata-rata {fmt_usd(tg_sales, 2)} per toko, "
                   f"{pct(tg_lift, 0, False)} di atas pekan non-libur "
                   f"({pct(tg_loc, 0, False)} di atas rata-rata 4 pekan di sekitarnya). "
                   f"Polanya muncul di setiap tahun yang tersedia ({int(hs_val('Thanksgiving', 'N'))} pekan Thanksgiving)."),
            aksi=["Pesan stok kategori permintaan tinggi 3-4 pekan sebelumnya.",
                  "Tambah jadwal karyawan & kasir sementara untuk pekan Thanksgiving.",
                  "Pusatkan anggaran promosi di sini, bukan di pekan libur yang lemah."],
            kpi="Stock-out rate, service level, penjualan pekan Thanksgiving vs tahun lalu"))

    # 2 --- Puncak Natal & minggu yang tidak terbaca Holiday_Flag
    dec_idx = si.get(12, np.nan)
    top = w.nlargest(5, "Total")
    unflag = top[top.Holiday == 0]
    if pd.notna(dec_idx):
        top_txt = ", ".join(f"{fmt_date(d)} ({fmt_usd(t)})" for d, t in zip(top.Date, top.Total)) if len(top) else "-"
        D.append(dict(
            prio="Tinggi", area="Perencanaan Puncak Musim",
            keputusan="Bentuk 'kalender puncak' sendiri: tambahkan pekan pra-Natal sebagai periode puncak, tidak bergantung pada Holiday_Flag.",
            bukti=(f"Penjualan Desember {pct(dec_idx, 0, False)} di atas rata-rata keseluruhan. Pekan tertinggi: {top_txt}. "
                   f"{len(unflag)} dari {len(top)} pekan tertinggi tidak ditandai sebagai hari libur "
                   f"(pekan pra-Natal tidak tertangkap Holiday_Flag)."),
            aksi=["Tambahkan flag 'Pra-Natal' (pekan 3 & 4 Desember) pada data & model forecast.",
                  "Kunci kapasitas gudang, transportasi, dan tenaga kerja sejak awal November.",
                  "Siapkan rencana cadangan stok untuk toko kelas A sebelum 15 Desember."],
            kpi="Fill rate pekan pra-Natal, lembur karyawan, penjualan per toko"))

    # 3 --- Januari & pasca-Natal
    jan_idx = si.get(1, np.nan)
    ny = hs_val("Natal / Akhir Tahun (pekan 30-31 Des)", "Lift_Global")
    if pd.notna(jan_idx):
        D.append(dict(
            prio="Menengah", area="Efisiensi Biaya",
            keputusan="Kurangi stok & jam kerja setelah Natal; manfaatkan Januari untuk clearance, pelatihan, dan perawatan toko.",
            bukti=(f"Penjualan Januari {pct(abs(jan_idx), 0, False)} di bawah rata-rata keseluruhan"
                   f"{' (bulan terlemah)' if jan_idx == si.min() else ''}. "
                   f"Pekan 30-31 Des tercatat {pct(ny, 0)} terhadap pekan non-libur, padahal ditandai sebagai libur."),
            aksi=["Jalankan promo clearance akhir Desember untuk menghabiskan stok musiman.",
                  "Turunkan order pembelian Januari sesuai indeks musiman.",
                  "Jadwalkan renovasi toko & pelatihan staf di Januari."],
            kpi="Inventory turnover, labor cost ratio, sisa stok musiman"))

    # 4 --- Lindungi toko kelas A
    nA = int((ss.Kelas == "A").sum())
    shareA = ss.loc[ss.Kelas == "A", "Share"].sum()
    top5 = ss.head(5)
    D.append(dict(
        prio="Tinggi", area="Alokasi Sumber Daya",
        keputusan="Prioritaskan alokasi stok, tenaga kerja, dan investasi ke toko kelas A (Pareto).",
        bukti=(f"{nA} dari {len(ss)} toko (kelas A) menyumbang {pct(shareA, 0, False)} penjualan. "
               f"5 toko teratas ({', '.join('Toko ' + str(int(s)) for s in top5.Store)}) = "
               f"{pct(top5.Share.sum(), 1, False)} total; 10 toko terbawah hanya "
               f"{pct(ss.tail(10).Share.sum(), 1, False)}."),
        aksi=["Terapkan target service level lebih tinggi di toko kelas A.",
              "Dahulukan toko kelas A saat pasokan terbatas di musim puncak.",
              "Pantau toko A dengan dashboard mingguan & alert penurunan."],
        kpi="Penjualan toko kelas A, stock-out rate, kepuasan pelanggan"))

    # 5 --- Toko menurun
    dec = gr[gr.G_last < 0]
    if len(gr.dropna(subset=["G_last"])):
        bigA = dec.merge(ss[["Store", "Kelas"]], on="Store")
        bigA = bigA[bigA.Kelas.isin(["A", "B"])]
        two = gr[(gr.G_last < 0) & (gr.G_prev < 0)]
        D.append(dict(
            prio="Tinggi", area="Perbaikan Kinerja Toko",
            keputusan="Lakukan audit khusus pada toko yang menurun, terutama toko bernilai besar atau turun dua tahun berturut-turut.",
            bukti=(f"{len(dec)} dari {len(gr)} toko turun pada {y_last} vs {y_prev} (periode Feb-Okt). "
                   f"Terbesar: {store_list(gr, 4, True, ss)}. "
                   f"{len(two)} toko turun dua tahun beruntun"
                   f"{' (' + ', '.join('Toko ' + str(int(s)) for s in two.Store) + ')' if len(two) else ''}. "
                   f"{len(bigA)} di antaranya kelas A/B (dampak revenue besar)."),
            aksi=["Audit: ketersediaan stok, assortment, harga kompetitor, dan kondisi lokal.",
                  "Bandingkan praktik dengan toko sebanding yang tumbuh.",
                  "Tetapkan target pemulihan 2 kuartal dan review bulanan."],
            kpi="Pertumbuhan YoY toko, traffic, ketersediaan stok"))

    # 6 --- Replikasi toko tumbuh
    if len(gr.dropna(subset=["G_last"])):
        D.append(dict(
            prio="Menengah", area="Pertumbuhan",
            keputusan="Pelajari dan replikasi praktik toko dengan pertumbuhan tertinggi; evaluasi potensi ekspansi kapasitas.",
            bukti=f"Pertumbuhan tertinggi: {store_list(gr, 5, False, ss)}. Banyak yang basisnya kecil (kelas B/C), sehingga ada ruang tumbuh.",
            aksi=["Dokumentasikan faktor sukses (assortment, promosi, lokasi, manajemen).",
                  "Uji coba (pilot) praktik tsb di toko serupa yang stagnan.",
                  "Tambah stok/ruang rak di toko tumbuh sebelum musim puncak."],
            kpi="Pertumbuhan toko hasil pilot vs kontrol"))

    # 7 --- Toko kelas C
    c = ss[ss.Kelas == "C"]
    if len(c):
        D.append(dict(
            prio="Menengah", area="Efisiensi Biaya",
            keputusan="Tinjau efisiensi toko kelas C (biaya, ukuran, assortment) sebelum menambah investasi.",
            bukti=(f"{len(c)} toko kelas C hanya menyumbang {pct(c.Share.sum(), 1, False)} penjualan; "
                   f"terendah: {', '.join('Toko ' + str(int(s)) for s in c.tail(3).Store)} "
                   f"(rata-rata {fmt_usd(c.Rata2.min())}/pekan)."),
            aksi=["Hitung profitabilitas (butuh data biaya & margin, belum ada di dataset).",
                  "Sesuaikan assortment dan jam operasional dengan permintaan lokal.",
                  "Jangan mengambil keputusan penutupan hanya dari data penjualan."],
            kpi="Margin per toko, biaya operasional per $ penjualan"))

    # 8 --- Volatilitas
    hi, lo = ss.nlargest(4, "CV"), ss.nsmallest(4, "CV")
    D.append(dict(
        prio="Menengah", area="Manajemen Stok",
        keputusan="Bedakan kebijakan safety stock: toko berfluktuasi tinggi butuh buffer & jadwal fleksibel, toko stabil bisa lean.",
        bukti=(f"Fluktuasi (CV) tertinggi: {', '.join(f'Toko {int(r.Store)} ({r.CV:.2f})' for _, r in hi.iterrows())}. "
               f"Paling stabil: {', '.join(f'Toko {int(r.Store)} ({r.CV:.2f})' for _, r in lo.iterrows())}."),
        aksi=["Naikkan safety stock & forecast mingguan untuk toko CV tinggi.",
              "Gunakan replenishment otomatis/just-in-time untuk toko stabil.",
              "Gunakan tenaga kerja fleksibel di toko CV tinggi."],
        kpi="Forecast accuracy (MAPE), stock-out, overstock"))

    # 9 --- Promo hari libur lemah
    sb, lb = hs_val("Super Bowl", "Lift_Global"), hs_val("Labor Day", "Lift_Global")
    if pd.notna(sb) or pd.notna(lb):
        D.append(dict(
            prio="Menengah", area="Promosi & Pemasaran",
            keputusan="Alihkan anggaran promosi dari hari libur berdampak rendah ke Thanksgiving & Desember.",
            bukti=f"Dampak Super Bowl {pct(sb, 1)} dan Labor Day {pct(lb, 1)} vs pekan non-libur, jauh di bawah Thanksgiving ({pct(tg_lift, 0)}).",
            aksi=["Kurangi diskon luas di Super Bowl & Labor Day.",
                  "Gunakan A/B test promo untuk menguji apakah ada kategori yang responsif.",
                  "Realokasikan anggaran ke pekan puncak."],
            kpi="ROI promosi per event, incremental sales"))

    # 10 --- Faktor makro
    mx = drv["Korelasi dgn Indeks Toko"].abs().max()
    unemp = drv.loc[drv.Faktor == "Unemployment", "Korelasi dgn Indeks Toko"].iloc[0]
    r2_store, r2_week = variance_explained(df)
    D.append(dict(
        prio="Rendah", area="Monitoring Eksternal",
        keputusan="Jangan menjadikan faktor makro (suhu, BBM, CPI, pengangguran) sebagai dasar utama keputusan; pakai sebagai sinyal pendukung.",
        bukti=(f"Korelasi terhadap indeks penjualan toko lemah (|r| maksimum = {mx:.2f}; pengangguran r = {unemp:.2f}). "
               f"Sebaliknya, identitas toko saja menjelaskan {pct(r2_store, 0, False)} variasi penjualan, dan pekan dalam tahun "
               f"menjelaskan {pct(r2_week, 0, False)} variasi sisanya (setelah skala toko dihilangkan)."),
        aksi=["Fokuskan model forecast pada toko, musim & event.",
              "Pantau pengangguran regional sebagai early-warning, bukan driver utama.",
              "Uji pengaruh lokal (per wilayah) sebelum mengubah strategi."],
        kpi="Peningkatan akurasi forecast saat faktor makro ditambahkan"))

    order = {"Tinggi": 0, "Menengah": 1, "Rendah": 2}
    return sorted(D, key=lambda d: order[d["prio"]])


def simulate(df, uplift_peak, recovery):
    """What-if sederhana (pendapatan, bukan laba)."""
    full = [y for y in df.Year.unique()
            if {11, 12}.issubset(set(df.loc[df.Year == y, "Month"]))]
    peak = df[df.Month.isin([11, 12]) & df.Year.isin(full)]
    peak_rev = peak.groupby("Year").Weekly_Sales.sum().mean() if len(full) else np.nan
    gr = store_growth(df)
    dec = gr[gr.G_last < 0]
    gap = ((dec.Rata_Sebelum - dec.Rata_Terakhir) * 52).sum() if len(dec) else 0.0
    return peak_rev, peak_rev * uplift_peak if pd.notna(peak_rev) else np.nan, gap, gap * recovery


# ----------------------------------------------------------------------------
# SIDEBAR & PEMUATAN DATA
# ----------------------------------------------------------------------------
st.sidebar.header("⚙️ Pengaturan")
uploaded = st.sidebar.file_uploader("Unggah CSV (opsional)", type="csv")

try:
    if uploaded is not None:
        df_all = load_data(uploaded)
    else:
        here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        path = next((p for p in (os.path.join(here, DEFAULT_FILE), DEFAULT_FILE) if os.path.exists(p)), None)
        if path is None:
            st.error(f"File '{DEFAULT_FILE}' tidak ditemukan. Letakkan di folder yang sama dengan app.py atau unggah lewat sidebar.")
            st.stop()
        df_all = load_data(path)
except ValueError as e:
    st.error(str(e))
    st.stop()

years_all = sorted(df_all.Year.unique().tolist())
stores_all = sorted(df_all.Store.unique().tolist())
sel_years = st.sidebar.multiselect("Tahun", years_all, default=years_all)
sel_stores = st.sidebar.multiselect("Toko", stores_all, default=stores_all)
st.sidebar.caption("Filter berlaku untuk tab 1-4. Tab 'Pusat Keputusan' selalu memakai seluruh data agar rekomendasi stabil.")

df = df_all[df_all.Year.isin(sel_years) & df_all.Store.isin(sel_stores)]
if df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Ringkasan Eksekutif", "🏬 Analisis Toko", "📅 Musiman & Hari Libur",
    "🌡️ Faktor Eksternal", "🎯 Pusat Keputusan"])

# ----------------------------------------------------------------------------
# TAB 1 - RINGKASAN
# ----------------------------------------------------------------------------
with tab1:
    g_all, g_years = overall_growth(df_all[df_all.Store.isin(sel_stores)])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Penjualan", fmt_usd(df.Weekly_Sales.sum(), 2))
    c2.metric("Rata-rata / Toko / Pekan", fmt_usd(df.Weekly_Sales.mean(), 0))
    c3.metric("Jumlah Toko", f"{df.Store.nunique()}")
    c4.metric("Pertumbuhan (Feb-Okt)", pct(g_all) if pd.notna(g_all) else "-",
              help=f"Rata-rata penjualan periode Feb-Okt {g_years[-1] if g_years else ''} vs tahun sebelumnya.")

    w = weekly_table(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=w.Date, y=w.Total, mode="lines", name="Total penjualan jaringan",
                             line=dict(color=BLUE, width=2)))
    hol = w[w.Holiday == 1]
    fig.add_trace(go.Scatter(x=hol.Date, y=hol.Total, mode="markers", name="Pekan libur (flag)",
                             marker=dict(color=YELLOW, size=10, line=dict(color=DARK, width=1))))
    fig.update_layout(title="Tren penjualan mingguan (total semua toko terpilih)", yaxis_title="USD")
    show(fig)

    ss = store_summary(df)
    colA, colB = st.columns(2)
    with colA:
        t = ss.head(10).copy()
        t["Store"] = "Toko " + t.Store.astype(int).astype(str)
        fig = px.bar(t.iloc[::-1], x="Total", y="Store", orientation="h",
                     title="10 toko dengan penjualan tertinggi", color_discrete_sequence=[BLUE])
        show(fig, 380)
    with colB:
        t = ss.tail(10).copy()
        t["Store"] = "Toko " + t.Store.astype(int).astype(str)
        fig = px.bar(t, x="Total", y="Store", orientation="h",
                     title="10 toko dengan penjualan terendah", color_discrete_sequence=[GREY])
        show(fig, 380)

# ----------------------------------------------------------------------------
# TAB 2 - TOKO
# ----------------------------------------------------------------------------
with tab2:
    st.subheader("Pareto & klasifikasi ABC toko")
    ss = store_summary(df)
    gr_sel = store_growth(df_all[df_all.Store.isin(sel_stores)])
    fig = go.Figure()
    fig.add_bar(x=ss.Store.astype(int).astype(str), y=ss.Total, name="Total penjualan",
                marker_color=[CLASS_COLOR[k] for k in ss.Kelas])
    fig.add_trace(go.Scatter(x=ss.Store.astype(int).astype(str), y=ss.CumShare * 100,
                             name="Kumulatif (%)", yaxis="y2", mode="lines+markers",
                             line=dict(color=DARK)))
    fig.update_layout(title="Pareto penjualan per toko (biru = A, kuning = B, abu = C)",
                      xaxis=dict(type="category", title="Toko"),
                      yaxis=dict(title="USD"),
                      yaxis2=dict(overlaying="y", side="right", range=[0, 105], title="Kumulatif (%)"))
    show(fig)
    k1, k2, k3 = st.columns(3)
    for col, k in zip((k1, k2, k3), ("A", "B", "C")):
        sub = ss[ss.Kelas == k]
        col.metric(f"Kelas {k}", f"{len(sub)} toko", f"{pct(sub.Share.sum(), 1, False)} penjualan", delta_color="off")

    st.subheader("Pertumbuhan vs skala toko")
    gm = ss.merge(gr_sel[["Store", "G_last"]], on="Store", how="left").dropna(subset=["G_last"])
    if len(gm):
        gm = gm.assign(Pertumbuhan=gm.G_last * 100, Label=gm.Store.astype(int).astype(str))
        fig = px.scatter(gm, x="Pertumbuhan", y="Rata2", size="Total", color="Kelas", text="Label",
                         hover_name="Label", color_discrete_map=CLASS_COLOR,
                         labels={"Pertumbuhan": "Pertumbuhan terakhir (%)", "Rata2": "Rata-rata penjualan/pekan (USD)"},
                         title="Kuadran toko: skala vs pertumbuhan")
        fig.add_vline(x=0, line_dash="dash", line_color=RED)
        fig.update_traces(textposition="top center")
        show(fig, 480)
        st.caption("Toko di kiri garis merah menurun. Toko besar (atas) yang menurun adalah prioritas audit.")
    else:
        st.info("Data tidak cukup untuk menghitung pertumbuhan (butuh minimal 2 tahun).")

    st.subheader("Volatilitas penjualan (CV = std / rata-rata)")
    t = ss.sort_values("CV", ascending=False).copy()
    t["Toko"] = t.Store.astype(int).astype(str)
    fig = px.bar(t, x="Toko", y="CV", color_discrete_sequence=[YELLOW],
                 title="Semakin tinggi CV, semakin sulit diprediksi (butuh safety stock lebih besar)")
    fig.update_xaxes(type="category")
    show(fig, 340)

    disp = ss.merge(gr_sel[["Store", "G_last"]], on="Store", how="left")
    disp["Share"] = disp.Share * 100
    disp["CumShare"] = disp.CumShare * 100
    disp["G_last"] = disp.G_last * 100
    table(disp[["Store", "Kelas", "Total", "Rata2", "CV", "Share", "CumShare", "G_last"]],
          column_config={"Total": st.column_config.NumberColumn("Total ($)", format="$%.0f"),
                         "Rata2": st.column_config.NumberColumn("Rata2/pekan ($)", format="$%.0f"),
                         "CV": st.column_config.NumberColumn("CV", format="%.3f"),
                         "Share": st.column_config.NumberColumn("Share (%)", format="%.2f"),
                         "CumShare": st.column_config.NumberColumn("Kumulatif (%)", format="%.1f"),
                         "G_last": st.column_config.NumberColumn("Pertumbuhan (%)", format="%.1f")})

# ----------------------------------------------------------------------------
# TAB 3 - MUSIMAN & HARI LIBUR
# ----------------------------------------------------------------------------
with tab3:
    st.subheader("Indeks musiman bulanan")
    si = seasonality(df)
    sdf = pd.DataFrame({"Bulan": [MONTH_ID[m] for m in si.index], "Indeks": si.values * 100,
                        "Arah": np.where(si.values >= 0, "Di atas rata-rata", "Di bawah rata-rata")})
    fig = px.bar(sdf, x="Bulan", y="Indeks", color="Arah",
                 color_discrete_map={"Di atas rata-rata": BLUE, "Di bawah rata-rata": GREY},
                 title="Penyimpangan penjualan vs rata-rata keseluruhan (%)")
    show(fig, 360)

    st.subheader("Pola mingguan per tahun")
    w = weekly_table(df)
    w["Tahun"] = w.Year.astype(str)
    fig = px.line(w.sort_values("Week"), x="Week", y="Total", color="Tahun",
                  title="Total penjualan per pekan ke-n dalam tahun",
                  color_discrete_sequence=[BLUE, YELLOW, DARK, RED])
    show(fig, 380)

    st.subheader("Dampak hari libur")
    ev = holiday_events(df)
    hs = holiday_summary(ev)
    if len(hs):
        fig = px.bar(hs.assign(Lift=hs.Lift_Global * 100), x="Event", y="Lift",
                     title="Rata-rata dampak pekan libur vs pekan non-libur (%)",
                     color_discrete_sequence=[BLUE], text="Lift")
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        show(fig, 380)
        t = hs.copy()
        t["Lift_Global"] *= 100
        t["Lift_Local"] *= 100
        table(t, column_config={
            "Rata2_Toko": st.column_config.NumberColumn("Rata2/toko ($)", format="$%.0f"),
            "Lift_Global": st.column_config.NumberColumn("Lift vs non-libur (%)", format="%.1f"),
            "Lift_Local": st.column_config.NumberColumn("Lift vs ±4 pekan (%)", format="%.1f"),
            "N": st.column_config.NumberColumn("Jumlah pekan")})
    else:
        st.info("Tidak ada pekan libur pada filter yang dipilih.")

    st.subheader("10 pekan dengan penjualan tertinggi")
    top = w.nlargest(10, "Total")[["Date", "Total", "Holiday"]].copy()
    top["Holiday"] = np.where(top.Holiday == 1, "Ya", "Tidak")
    top["Date"] = top.Date.apply(fmt_date)
    table(top, column_config={"Total": st.column_config.NumberColumn("Total ($)", format="$%.0f"),
                              "Holiday": st.column_config.TextColumn("Ditandai libur?")})
    st.caption("Perhatikan: pekan puncak sebelum Natal sering tidak ditandai sebagai libur pada Holiday_Flag.")

# ----------------------------------------------------------------------------
# TAB 4 - FAKTOR EKSTERNAL
# ----------------------------------------------------------------------------
with tab4:
    drv, dd = driver_table(df)
    st.subheader("Korelasi faktor eksternal dengan penjualan")
    long = drv.melt(id_vars="Faktor", var_name="Metode", value_name="r")
    fig = px.bar(long, x="Faktor", y="r", color="Metode", barmode="group",
                 color_discrete_sequence=[BLUE, YELLOW], title="Koefisien korelasi Pearson")
    fig.update_yaxes(range=[-1, 1])
    show(fig, 360)
    st.caption("Indeks toko = penjualan dibagi rata-rata tokonya, sehingga perbedaan skala antar toko tidak mengacaukan analisis. "
               "Korelasi lemah (|r| < 0.3) artinya faktor tsb bukan penentu utama.")

    left, right = st.columns(2)
    with left:
        samp = dd.sample(min(len(dd), 2500), random_state=1)
        fig = px.scatter(samp, x="Unemployment", y="Indeks", opacity=0.35,
                         color_discrete_sequence=[BLUE], title="Pengangguran vs indeks penjualan toko")
        if dd.Unemployment.nunique() > 1:
            k, b = np.polyfit(dd.Unemployment, dd.Indeks, 1)
            xs = np.array([dd.Unemployment.min(), dd.Unemployment.max()])
            fig.add_trace(go.Scatter(x=xs, y=k * xs + b, mode="lines", name="Tren",
                                     line=dict(color=RED, width=3)))
        show(fig, 380)
    with right:
        bins = pd.cut(dd.Temperature, [-20, 40, 60, 80, 120], labels=["<40°F", "40-60°F", "60-80°F", ">80°F"])
        tb = dd.groupby(bins, observed=True).Indeks.mean().reset_index()
        tb.columns = ["Suhu", "Indeks"]
        fig = px.bar(tb, x="Suhu", y="Indeks", color_discrete_sequence=[YELLOW],
                     title="Indeks penjualan menurut rentang suhu")
        show(fig, 380)
    st.warning("Hati-hati: suhu berkorelasi dengan musim (Desember dingin sekaligus puncak belanja), "
               "sehingga hubungan di atas tidak boleh dibaca sebagai sebab-akibat.")

# ----------------------------------------------------------------------------
# TAB 5 - PUSAT KEPUTUSAN
# ----------------------------------------------------------------------------
with tab5:
    st.subheader("🎯 Rekomendasi keputusan berbasis data")
    st.caption("Dihitung dari seluruh data. Angka di bawah dihasilkan otomatis dari dataset Anda.")
    icon = {"Tinggi": "🔴", "Menengah": "🟠", "Rendah": "🟢"}
    decisions = build_decisions(df_all)

    n_hi = sum(d["prio"] == "Tinggi" for d in decisions)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total keputusan", len(decisions))
    m2.metric("Prioritas tinggi", n_hi)
    m3.metric("Area tercakup", len({d["area"] for d in decisions}))

    for i, d in enumerate(decisions, 1):
        with st.container(border=True):
            st.markdown(f"**{icon[d['prio']]} Keputusan {i} - {d['keputusan']}**")
            st.caption(f"Prioritas: {d['prio']}  |  Area: {d['area']}")
            st.markdown(f"**Bukti data:** {d['bukti']}")
            st.markdown("**Tindakan:**\n" + "\n".join(f"- {a}" for a in d["aksi"]))
            st.markdown(f"**KPI pemantauan:** {d['kpi']}")

    st.divider()
    st.subheader("Rekomendasi tindakan per toko")
    ss_all, gr_all = store_summary(df_all), store_growth(df_all)
    acts = store_actions(ss_all, gr_all)
    pick = st.multiselect("Filter rekomendasi", sorted(acts.Rekomendasi.unique()),
                          default=sorted(acts.Rekomendasi.unique()))
    view = acts[acts.Rekomendasi.isin(pick)].copy()
    view["Share"] *= 100
    view["G_last"] *= 100
    view["G_prev"] *= 100
    table(view[["Store", "Kelas", "Rata2", "Share", "G_prev", "G_last", "Rekomendasi"]],
          column_config={"Rata2": st.column_config.NumberColumn("Rata2/pekan ($)", format="$%.0f"),
                         "Share": st.column_config.NumberColumn("Share (%)", format="%.2f"),
                         "G_prev": st.column_config.NumberColumn("Pertumbuhan sebelumnya (%)", format="%.1f"),
                         "G_last": st.column_config.NumberColumn("Pertumbuhan terakhir (%)", format="%.1f")})
    st.download_button("⬇️ Unduh rekomendasi per toko (CSV)",
                       acts.to_csv(index=False).encode("utf-8"),
                       file_name="rekomendasi_toko.csv", mime="text/csv")

    st.divider()
    st.subheader("🧮 Simulasi what-if (dampak pendapatan)")
    s1, s2 = st.columns(2)
    up = s1.slider("Kenaikan penjualan Nov-Des dari stok & staf yang lebih siap (%)",
                   min_value=0.0, max_value=10.0, value=3.0, step=0.5)
    rec = s2.slider("Persentase penurunan toko yang berhasil dipulihkan (%)",
                    min_value=0, max_value=100, value=50, step=5)
    peak_rev, peak_gain, gap, gap_gain = simulate(df_all, up / 100, rec / 100)
    r1, r2, r3 = st.columns(3)
    r1.metric("Pendapatan Nov-Des (per tahun)", fmt_usd(peak_rev))
    r2.metric("Tambahan dari kesiapan musim puncak", fmt_usd(peak_gain))
    r3.metric("Tambahan dari pemulihan toko menurun", fmt_usd(gap_gain),
              help=f"Selisih tahunan penjualan toko menurun terhadap tahun sebelumnya: {fmt_usd(gap)}")
    st.caption("Ini simulasi pendapatan dengan asumsi sederhana, bukan laba: dataset tidak memuat biaya atau margin. "
               "Gunakan sebagai gambaran skala prioritas, bukan ramalan.")
