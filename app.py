"""
Walmart Business Intelligence - Decision Support Dashboard
===========================================================
Dashboard pendukung pengambilan keputusan berbasis data penjualan mingguan Walmart.

Cara menjalankan:
    streamlit run app.py

Berkas data:
    Walmart_Cleaned.csv (letakkan satu folder dengan app.py) atau unggah melalui sidebar.

Susunan aplikasi:
    1. Ringkasan Eksekutif   - KPI dan tren penjualan
    2. Analisis Toko         - Pareto/ABC, pertumbuhan, volatilitas
    3. Musiman & Hari Libur  - indeks bulanan, dampak hari libur, pekan puncak
    4. Faktor Eksternal      - suhu, BBM, CPI, pengangguran
    5. Pusat Keputusan       - rekomendasi keputusan berbasis data + simulasi what-if

Disusun oleh : Kelompok Mahasiswa
Mata Kuliah  : Business Intelligence / Analitik Data
"""

import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# KONFIGURASI HALAMAN
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


# ----------------------------------------------------------------------------
# GAYA VISUAL & HERO
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <style>
    .hero {{
        background: linear-gradient(90deg, {DARK}, {BLUE});
        padding: 1.4rem 1.8rem;
        border-radius: 14px;
        color: white;
        margin-bottom: 1.2rem;
    }}
    .hero h1 {{ color: white; margin: 0; font-size: 1.85rem; letter-spacing: .3px; }}
    .hero p  {{ color: #dce9f7; margin: .45rem 0 0 0; font-size: 1rem; }}
    .hero .meta {{ color: #ffd966; margin-top: .55rem; font-size: .88rem; }}

    .interp {{
        background: #f4f8fc;
        border-left: 4px solid {BLUE};
        padding: .85rem 1.1rem;
        border-radius: 6px;
        margin: .7rem 0;
        color: #1f2a37;
    }}
    .interp b {{ color: {DARK}; }}

    .note {{
        background: #fff8e1;
        border-left: 4px solid {YELLOW};
        padding: .75rem 1rem;
        border-radius: 6px;
        margin: .6rem 0;
        color: #4a3b00;
    }}

    .kpi-box {{
        background: white;
        border: 1px solid #e5e9ef;
        border-radius: 10px;
        padding: .8rem 1rem;
        margin-bottom: .4rem;
    }}

    h3 {{ color: {DARK}; }}
    </style>
    <div class="hero">
      <h1>🛒 Walmart Business Intelligence</h1>
      <p>Dashboard Pendukung Pengambilan Keputusan Berbasis Data Penjualan Mingguan</p>
      <div class="meta">Proyek Kelompok Mahasiswa &middot; Analisis Data Penjualan Ritel</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# HELPER TAMPILAN
# ----------------------------------------------------------------------------
def show(fig, height=420):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=10, t=55, b=10),
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


def interpretasi(judul, teks):
    """Kotak interpretasi resmi kelompok."""
    st.markdown(
        f'<div class="interp"><b>{judul}</b><br>{teks}</div>',
        unsafe_allow_html=True,
    )


def catatan(teks):
    """Kotak catatan / peringatan metodologis."""
    st.markdown(f'<div class="note"><b>📌 Catatan Metodologis:</b> {teks}</div>',
                unsafe_allow_html=True)


def divider():
    st.markdown("---")


# ----------------------------------------------------------------------------
# PEMUATAN DATA
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
# FUNGSI ANALISIS
# ----------------------------------------------------------------------------
def weekly_table(df):
    w = (df.groupby("Date")
           .agg(Sales=("Weekly_Sales", "mean"),
                Total=("Weekly_Sales", "sum"),
                Holiday=("Holiday_Flag", "max"))
           .reset_index())
    w["Year"] = w["Date"].dt.year
    w["Week"] = w["Date"].dt.isocalendar().week.astype(int)
    return w


def store_summary(df):
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
    m = df.groupby("Month").Weekly_Sales.mean()
    return m / df.Weekly_Sales.mean() - 1


def holiday_events(df):
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
    m = ss.merge(gr[["Store", "G_last", "G_prev"]], on="Store", how="left")

    def act(r):
        g = r["G_last"]
        if pd.isna(g):
            return "⚪ Pantau"
        if r["Kelas"] == "A" and g < 0:
            return "🔴 Prioritaskan - audit penyebab penurunan"
        if r["Kelas"] == "A":
            return "🟢 Pertahankan - jaga stok & layanan"
        if g >= 0.03:
            return "🔵 Kembangkan - tambah stok/ruang & promo"
        if r["Kelas"] == "B" and g < 0:
            return "🟠 Perbaiki - tinjau assortment & promo lokal"
        if r["Kelas"] == "C" and g < 0:
            return "🟠 Evaluasi efisiensi biaya"
        return "⚪ Pantau"

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
# MESIN KEPUTUSAN (bahasa kelompok mahasiswa, formal)
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

    # 1 — Thanksgiving
    tg_lift, tg_loc = hs_val("Thanksgiving", "Lift_Global"), hs_val("Thanksgiving", "Lift_Local")
    tg_sales = hs_val("Thanksgiving", "Rata2_Toko")
    if pd.notna(tg_lift):
        D.append(dict(
            prio="Tinggi", area="Inventori & Tenaga Kerja",
            keputusan=("Kelompok kami merekomendasikan pekan Thanksgiving dijadikan sebagai "
                       "prioritas utama dalam perencanaan inventori dan penjadwalan tenaga kerja."),
            bukti=(f"Berdasarkan pengolahan data, pekan Thanksgiving menghasilkan rata-rata "
                   f"{fmt_usd(tg_sales, 2)} per toko, yaitu {pct(tg_lift, 0, False)} di atas pekan "
                   f"non-libur dan {pct(tg_loc, 0, False)} di atas rata-rata empat pekan di sekitarnya. "
                   f"Pola ini konsisten pada seluruh tahun pengamatan "
                   f"({int(hs_val('Thanksgiving', 'N'))} pekan Thanksgiving), sehingga kami menilai "
                   f"temuan ini cukup andal sebagai dasar keputusan."),
            aksi=["Kami mengusulkan pemesanan stok untuk kategori permintaan tinggi dilakukan "
                  "3–4 pekan sebelum pekan Thanksgiving.",
                  "Penambahan jadwal karyawan dan kasir sementara pada pekan tersebut perlu "
                  "direncanakan lebih awal.",
                  "Anggaran promosi sebaiknya dipusatkan pada pekan Thanksgiving, bukan pada "
                  "pekan libur yang dampaknya lemah."],
            kpi="Tingkat stock-out, service level, dan perbandingan penjualan pekan Thanksgiving antar tahun."))

    # 2 — Puncak Natal & minggu pra-Natal
    dec_idx = si.get(12, np.nan)
    top = w.nlargest(5, "Total")
    unflag = top[top.Holiday == 0]
    if pd.notna(dec_idx):
        top_txt = ", ".join(f"{fmt_date(d)} ({fmt_usd(t)})" for d, t in zip(top.Date, top.Total)) if len(top) else "-"
        D.append(dict(
            prio="Tinggi", area="Perencanaan Puncak Musim",
            keputusan=("Kelompok kami menyarankan pembentukan 'kalender puncak' internal: pekan "
                       "pra-Natal perlu diperlakukan sebagai periode puncak meskipun tidak "
                       "tertandai oleh Holiday_Flag."),
            bukti=(f"Hasil analisis menunjukkan penjualan Desember {pct(dec_idx, 0, False)} di atas "
                   f"rata-rata keseluruhan. Pekan tertinggi: {top_txt}. "
                   f"{len(unflag)} dari {len(top)} pekan tertinggi tidak ditandai sebagai hari libur, "
                   f"yang berarti pekan pra-Natal tidak tertangkap oleh Holiday_Flag."),
            aksi=["Kami mengusulkan penambahan flag 'Pra-Natal' (pekan 3 dan 4 Desember) pada data "
                  "maupun model peramalan.",
                  "Kapasitas gudang, transportasi, dan tenaga kerja sebaiknya dikunci sejak awal November.",
                  "Rencana cadangan stok untuk toko kelas A perlu disiapkan sebelum 15 Desember."],
            kpi="Fill rate pekan pra-Natal, lembur karyawan, penjualan per toko."))

    # 3 — Januari & pasca-Natal
    jan_idx = si.get(1, np.nan)
    ny = hs_val("Natal / Akhir Tahun (pekan 30-31 Des)", "Lift_Global")
    if pd.notna(jan_idx):
        D.append(dict(
            prio="Menengah", area="Efisiensi Biaya",
            keputusan=("Kelompok kami merekomendasikan pengurangan stok dan jam kerja setelah Natal, "
                       "serta pemanfaatan Januari untuk clearance, pelatihan, dan perawatan toko."),
            bukti=(f"Data menunjukkan penjualan Januari {pct(abs(jan_idx), 0, False)} di bawah rata-rata "
                   f"keseluruhan{' (bulan terlemah)' if jan_idx == si.min() else ''}. "
                   f"Pekan 30-31 Desember tercatat {pct(ny, 0)} terhadap pekan non-libur, padahal "
                   f"ditandai sebagai pekan libur."),
            aksi=["Kami mengusulkan promo clearance akhir Desember untuk menghabiskan stok musiman.",
                  "Pesanan pembelian Januari sebaiknya diturunkan mengikuti indeks musiman.",
                  "Renovasi toko dan pelatihan staf sebaiknya dijadwalkan pada Januari."],
            kpi="Inventory turnover, labor cost ratio, sisa stok musiman."))

    # 4 — Lindungi toko kelas A
    nA = int((ss.Kelas == "A").sum())
    shareA = ss.loc[ss.Kelas == "A", "Share"].sum()
    top5 = ss.head(5)
    D.append(dict(
        prio="Tinggi", area="Alokasi Sumber Daya",
        keputusan=("Kelompok kami merekomendasikan prioritas alokasi stok, tenaga kerja, dan "
                   "investasi pada toko kelas A (prinsip Pareto)."),
        bukti=(f"Hasil klasifikasi ABC menunjukkan {nA} dari {len(ss)} toko (kelas A) menyumbang "
               f"{pct(shareA, 0, False)} penjualan. Lima toko teratas "
               f"({', '.join('Toko ' + str(int(s)) for s in top5.Store)}) menyumbang "
               f"{pct(top5.Share.sum(), 1, False)}, sedangkan 10 toko terbawah hanya "
               f"{pct(ss.tail(10).Share.sum(), 1, False)}."),
        aksi=["Kami mengusulkan target service level yang lebih tinggi untuk toko kelas A.",
              "Saat pasokan terbatas di musim puncak, toko kelas A perlu didahulukan.",
              "Pemantauan toko kelas A sebaiknya dilakukan mingguan dengan alert penurunan."],
        kpi="Penjualan toko kelas A, stock-out rate, kepuasan pelanggan."))

    # 5 — Toko menurun
    dec = gr[gr.G_last < 0]
    if len(gr.dropna(subset=["G_last"])):
        bigA = dec.merge(ss[["Store", "Kelas"]], on="Store")
        bigA = bigA[bigA.Kelas.isin(["A", "B"])]
        two = gr[(gr.G_last < 0) & (gr.G_prev < 0)]
        D.append(dict(
            prio="Tinggi", area="Perbaikan Kinerja Toko",
            keputusan=("Kelompok kami mengusulkan audit khusus pada toko yang menurun, terutama "
                       "toko bernilai besar atau yang turun dua tahun berturut-turut."),
            bukti=(f"Analisis pertumbuhan (Feb–Okt) menunjukkan {len(dec)} dari {len(gr)} toko "
                   f"mengalami penurunan pada {y_last} dibandingkan {y_prev}. "
                   f"Penurunan terbesar: {store_list(gr, 4, True, ss)}. "
                   f"Sebanyak {len(two)} toko turun dua tahun berturut-turut"
                   f"{' (' + ', '.join('Toko ' + str(int(s)) for s in two.Store) + ')' if len(two) else ''}, "
                   f"dan {len(bigA)} di antaranya tergolong kelas A/B sehingga berdampak besar pada pendapatan."),
            aksi=["Audit mencakup ketersediaan stok, assortment, harga kompetitor, dan kondisi lokal.",
                  "Praktik toko yang menurun sebaiknya dibandingkan dengan toko sebanding yang tumbuh.",
                  "Kami mengusulkan target pemulihan dua kuartal dengan review bulanan."],
            kpi="Pertumbuhan YoY toko, traffic, dan ketersediaan stok."))

    # 6 — Replikasi toko tumbuh
    if len(gr.dropna(subset=["G_last"])):
        D.append(dict(
            prio="Menengah", area="Pertumbuhan",
            keputusan=("Kelompok kami merekomendasikan pembelajaran dan replikasi praktik toko "
                       "dengan pertumbuhan tertinggi, sekaligus evaluasi potensi ekspansi kapasitas."),
            bukti=(f"Pertumbuhan tertinggi dicapai oleh: {store_list(gr, 5, False, ss)}. "
                   f"Sebagian besar memiliki basis penjualan kecil (kelas B/C), sehingga masih "
                   f"terdapat ruang tumbuh yang cukup besar."),
            aksi=["Faktor keberhasilan (assortment, promosi, lokasi, manajemen) perlu didokumentasikan.",
                  "Uji coba (pilot) praktik tersebut di toko serupa yang stagnan.",
                  "Penambahan stok/ruang rak di toko tumbuh sebaiknya dilakukan sebelum musim puncak."],
            kpi="Pertumbuhan toko hasil pilot dibandingkan toko kontrol."))

    # 7 — Toko kelas C
    c = ss[ss.Kelas == "C"]
    if len(c):
        D.append(dict(
            prio="Menengah", area="Efisiensi Biaya",
            keputusan=("Kelompok kami menyarankan peninjauan efisiensi toko kelas C (biaya, ukuran, "
                       "assortment) sebelum menambah investasi baru."),
            bukti=(f"Toko kelas C berjumlah {len(c)} unit dan hanya menyumbang "
                   f"{pct(c.Share.sum(), 1, False)} penjualan; penjualan terendah: "
                   f"{', '.join('Toko ' + str(int(s)) for s in c.tail(3).Store)} "
                   f"(rata-rata {fmt_usd(c.Rata2.min())}/pekan)."),
            aksi=["Profitabilitas perlu dihitung terlebih dahulu (memerlukan data biaya & margin "
                  "yang belum tersedia pada dataset).",
                  "Assortment dan jam operasional sebaiknya disesuaikan dengan permintaan lokal.",
                  "Kami menegaskan bahwa keputusan penutupan tidak boleh diambil hanya dari data penjualan."],
            kpi="Margin per toko, biaya operasional per dolar penjualan."))

    # 8 — Volatilitas
    hi, lo = ss.nlargest(4, "CV"), ss.nsmallest(4, "CV")
    D.append(dict(
        prio="Menengah", area="Manajemen Stok",
        keputusan=("Kelompok kami mengusulkan pembedaan kebijakan safety stock: toko berfluktuasi "
                   "tinggi membutuhkan buffer dan jadwal fleksibel, sedangkan toko stabil dapat "
                   "diterapkan kebijakan lean."),
        bukti=(f"Fluktuasi (CV) tertinggi: {', '.join(f'Toko {int(r.Store)} ({r.CV:.2f})' for _, r in hi.iterrows())}. "
               f"Toko paling stabil: {', '.join(f'Toko {int(r.Store)} ({r.CV:.2f})' for _, r in lo.iterrows())}."),
        aksi=["Safety stock dan peramalan mingguan dinaikkan untuk toko dengan CV tinggi.",
              "Replenishment otomatis/just-in-time dapat diterapkan untuk toko stabil.",
              "Tenaga kerja fleksibel lebih sesuai untuk toko dengan CV tinggi."],
        kpi="Forecast accuracy (MAPE), stock-out, dan overstock."))

    # 9 — Promo hari libur lemah
    sb, lb = hs_val("Super Bowl", "Lift_Global"), hs_val("Labor Day", "Lift_Global")
    if pd.notna(sb) or pd.notna(lb):
        D.append(dict(
            prio="Menengah", area="Promosi & Pemasaran",
            keputusan=("Kelompok kami merekomendasikan pengalihan anggaran promosi dari hari libur "
                       "berdampak rendah ke pekan Thanksgiving dan Desember."),
            bukti=(f"Dampak Super Bowl {pct(sb, 1)} dan Labor Day {pct(lb, 1)} terhadap pekan non-libur "
                   f"jauh lebih rendah dibandingkan Thanksgiving ({pct(tg_lift, 0)})."),
            aksi=["Diskon luas pada Super Bowl dan Labor Day sebaiknya dikurangi.",
                  "A/B test promo perlu dilakukan untuk menguji apakah ada kategori yang responsif.",
                  "Anggaran sebaiknya direalokasikan ke pekan puncak."],
            kpi="ROI promosi per event dan incremental sales."))

    # 10 — Faktor makro
    mx = drv["Korelasi dgn Indeks Toko"].abs().max()
    unemp = drv.loc[drv.Faktor == "Unemployment", "Korelasi dgn Indeks Toko"].iloc[0]
    r2_store, r2_week = variance_explained(df)
    D.append(dict(
        prio="Rendah", area="Monitoring Eksternal",
        keputusan=("Kelompok kami berpendapat faktor makro (suhu, BBM, CPI, pengangguran) tidak "
                   "dijadikan dasar utama keputusan, melainkan sebagai sinyal pendukung."),
        bukti=(f"Korelasi terhadap indeks penjualan toko tergolong lemah (|r| maksimum = {mx:.2f}; "
               f"pengangguran r = {unemp:.2f}). Sebaliknya, identitas toko saja menjelaskan "
               f"{pct(r2_store, 0, False)} variasi penjualan, dan pekan dalam tahun menjelaskan "
               f"{pct(r2_week, 0, False)} variasi sisanya (setelah skala toko dihilangkan)."),
        aksi=["Model peramalan sebaiknya difokuskan pada toko, musim, dan event.",
              "Pengangguran regional dipantau sebagai early-warning, bukan sebagai driver utama.",
              "Pengaruh lokal (per wilayah) perlu diuji sebelum strategi diubah."],
        kpi="Peningkatan akurasi peramalan saat faktor makro ditambahkan."))

    order = {"Tinggi": 0, "Menengah": 1, "Rendah": 2}
    return sorted(D, key=lambda d: order[d["prio"]])


def simulate(df, uplift_peak, recovery):
    full = [y for y in df.Year.unique()
            if {11, 12}.issubset(set(df.loc[df.Year == y, "Month"]))]
    peak = df[df.Month.isin([11, 12]) & df.Year.isin(full)]
    peak_rev = peak.groupby("Year").Weekly_Sales.sum().mean() if len(full) else np.nan
    gr = store_growth(df)
    dec = gr[gr.G_last < 0]
    gap = ((dec.Rata_Sebelum - dec.Rata_Terakhir) * 52).sum() if len(dec) else 0.0
    return peak_rev, peak_rev * uplift_peak if pd.notna(peak_rev) else np.nan, gap, gap * recovery


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
st.sidebar.markdown("## ⚙️ Panel Pengaturan")
st.sidebar.caption("Gunakan panel ini untuk memilih berkas data dan memfilter "
                   "periode serta toko yang ingin dianalisis.")

with st.sidebar.expander("📂 Sumber Data", expanded=True):
    uploaded = st.sidebar.file_uploader("Unggah berkas CSV (opsional)", type="csv")
    st.caption(f"Jika tidak diunggah, sistem otomatis membaca `{DEFAULT_FILE}` "
               f"dari folder aplikasi.")

try:
    if uploaded is not None:
        df_all = load_data(uploaded)
    else:
        here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        path = next((p for p in (os.path.join(here, DEFAULT_FILE), DEFAULT_FILE) if os.path.exists(p)), None)
        if path is None:
            st.error(f"Berkas '{DEFAULT_FILE}' tidak ditemukan. Silakan letakkan pada folder yang sama "
                     f"dengan app.py atau unggah melalui sidebar.")
            st.stop()
        df_all = load_data(path)
except ValueError as e:
    st.error(str(e))
    st.stop()

years_all = sorted(df_all.Year.unique().tolist())
stores_all = sorted(df_all.Store.unique().tolist())

with st.sidebar.expander("🔎 Filter Data", expanded=True):
    sel_years = st.multiselect("Tahun", years_all, default=years_all)
    sel_stores = st.multiselect("Toko", stores_all, default=stores_all)
    st.caption("Filter berlaku untuk tab 1–4. Tab **Pusat Keputusan** selalu menggunakan "
               "seluruh data agar rekomendasi tetap stabil dan konsisten.")

df = df_all[df_all.Year.isin(sel_years) & df_all.Store.isin(sel_stores)]
if df.empty:
    st.warning("Tidak ada data yang sesuai dengan filter yang dipilih. Silakan sesuaikan filter pada sidebar.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(f"Data aktif: **{len(df):,} baris** · "
                   f"**{df.Store.nunique()} toko** · "
                   f"**{df.Year.nunique()} tahun**")

# ----------------------------------------------------------------------------
# TAB
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Ringkasan Eksekutif", "🏬 Analisis Toko", "📅 Musiman & Hari Libur",
    "🌡️ Faktor Eksternal", "🎯 Pusat Keputusan"])

# ============================================================================
# TAB 1 — RINGKASAN EKSEKUTIF
# ============================================================================
with tab1:
    st.markdown("### Gambaran Umum Kinerja Penjualan")
    st.markdown(
        "Bagian ini menyajikan ringkasan indikator utama sebagai titik tolak analisis. "
        "Angka-angka yang ditampilkan merupakan hasil agregasi dari data yang telah difilter "
        "pada sidebar, sehingga pembaca dapat menyesuaikan cakupan analisis sesuai kebutuhan."
    )

    g_all, g_years = overall_growth(df_all[df_all.Store.isin(sel_stores)])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Penjualan", fmt_usd(df.Weekly_Sales.sum(), 2),
              help="Akumulasi penjualan seluruh toko terpilih selama periode amatan.")
    c2.metric("Rata-rata / Toko / Pekan", fmt_usd(df.Weekly_Sales.mean(), 0),
              help="Rata-rata penjualan mingguan per toko; menggambarkan skala tipikal operasional.")
    c3.metric("Jumlah Toko", f"{df.Store.nunique()}",
              help="Banyaknya toko yang dianalisis pada filter saat ini.")
    c4.metric("Pertumbuhan (Feb–Okt)", pct(g_all) if pd.notna(g_all) else "-",
              help=(f"Perbandingan rata-rata penjualan periode Feb–Okt "
                    f"{g_years[-1] if g_years else ''} terhadap tahun sebelumnya. "
                    f"Periode dipilih agar perbandingan bersifat apple-to-apple."))

    divider()
    st.markdown("#### Tren Penjualan Mingguan")
    st.caption("Total penjualan seluruh toko terpilih per pekan. Titik kuning menandai pekan "
               "yang diberi flag libur (Holiday_Flag = 1).")

    w = weekly_table(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=w.Date, y=w.Total, mode="lines", name="Total penjualan jaringan",
                             line=dict(color=BLUE, width=2)))
    hol = w[w.Holiday == 1]
    fig.add_trace(go.Scatter(x=hol.Date, y=hol.Total, mode="markers", name="Pekan libur (flag)",
                             marker=dict(color=YELLOW, size=10, line=dict(color=DARK, width=1))))
    fig.update_layout(title="Tren Penjualan Mingguan (Total Semua Toko Terpilih)",
                      yaxis_title="USD", xaxis_title="Tanggal")
    show(fig)

    interpretasi(
        "Interpretasi Kelompok",
        "Pola grafik memperlihatkan adanya lonjakan berulang pada periode akhir tahun, "
        "khususnya menjelang Thanksgiving dan Natal. Lonjakan ini perlu menjadi perhatian "
        "utama dalam perencanaan kapasitas maupun stok, karena berdampak langsung pada "
        "kesiapan operasional toko."
    )

    divider()
    st.markdown("#### Distribusi Penjualan Antar Toko")
    st.caption("Sepuluh toko dengan penjualan tertinggi dan terendah selama periode amatan.")

    ss = store_summary(df)
    colA, colB = st.columns(2)
    with colA:
        t = ss.head(10).copy()
        t["Store"] = "Toko " + t.Store.astype(int).astype(str)
        fig = px.bar(t.iloc[::-1], x="Total", y="Store", orientation="h",
                     title="10 Toko dengan Penjualan Tertinggi",
                     color_discrete_sequence=[BLUE])
        show(fig, 380)
    with colB:
        t = ss.tail(10).copy()
        t["Store"] = "Toko " + t.Store.astype(int).astype(str)
        fig = px.bar(t, x="Total", y="Store", orientation="h",
                     title="10 Toko dengan Penjualan Terendah",
                     color_discrete_sequence=[GREY])
        show(fig, 380)

    interpretasi(
        "Interpretasi Kelompok",
        "Terdapat kesenjangan yang sangat mencolok antara toko berpenjualan tinggi dan rendah. "
        "Ketimpangan ini menjadi dasar bagi kami untuk menerapkan klasifikasi ABC pada tab "
        "berikutnya, sehingga alokasi sumber daya dapat lebih tepat sasaran."
    )

# ============================================================================
# TAB 2 — ANALISIS TOKO
# ============================================================================
with tab2:
    st.markdown("### Klasifikasi dan Kinerja per Toko")
    st.markdown(
        "Bagian ini membahas karakteristik setiap toko dari tiga sudut pandang: kontribusi "
        "penjualan (Pareto/ABC), pertumbuhan antar tahun, dan volatilitas penjualan. "
        "Ketiga sudut pandang ini kami gunakan sebagai dasar penentuan prioritas tindakan."
    )

    divider()
    st.markdown("#### 1) Pareto dan Klasifikasi ABC")
    st.caption("Kelas A mencakup sekitar 70% kumulatif penjualan, kelas B sampai 90%, "
               "dan sisanya kelas C.")

    ss = store_summary(df)
    gr_sel = store_growth(df_all[df_all.Store.isin(sel_stores)])

    fig = go.Figure()
    fig.add_bar(x=ss.Store.astype(int).astype(str), y=ss.Total, name="Total penjualan",
                marker_color=[CLASS_COLOR[k] for k in ss.Kelas])
    fig.add_trace(go.Scatter(x=ss.Store.astype(int).astype(str), y=ss.CumShare * 100,
                             name="Kumulatif (%)", yaxis="y2", mode="lines+markers",
                             line=dict(color=DARK)))
    fig.update_layout(title="Diagram Pareto Penjualan per Toko (biru = A, kuning = B, abu = C)",
                      xaxis=dict(type="category", title="Toko"),
                      yaxis=dict(title="USD"),
                      yaxis2=dict(overlaying="y", side="right", range=[0, 105], title="Kumulatif (%)"))
    show(fig)

    k1, k2, k3 = st.columns(3)
    for col, k in zip((k1, k2, k3), ("A", "B", "C")):
        sub = ss[ss.Kelas == k]
        col.metric(f"Kelas {k}", f"{len(sub)} toko",
                   f"{pct(sub.Share.sum(), 1, False)} penjualan", delta_color="off")

    interpretasi(
        "Interpretasi Kelompok",
        "Prinsip Pareto terkonfirmasi pada data ini: sebagian kecil toko menyumbang mayoritas "
        "penjualan. Oleh karena itu, kami menilai bahwa prioritas alokasi sumber daya sebaiknya "
        "diberikan kepada toko kelas A, tanpa mengabaikan upaya efisiensi pada kelas C."
    )

    divider()
    st.markdown("#### 2) Pertumbuhan vs Skala Toko")
    st.caption("Setiap titik mewakili satu toko. Garis merah putus-putus menandai pertumbuhan 0%.")

    gm = ss.merge(gr_sel[["Store", "G_last"]], on="Store", how="left").dropna(subset=["G_last"])
    if len(gm):
        gm = gm.assign(Pertumbuhan=gm.G_last * 100, Label=gm.Store.astype(int).astype(str))
        fig = px.scatter(gm, x="Pertumbuhan", y="Rata2", size="Total", color="Kelas", text="Label",
                         hover_name="Label", color_discrete_map=CLASS_COLOR,
                         labels={"Pertumbuhan": "Pertumbuhan terakhir (%)",
                                 "Rata2": "Rata-rata penjualan/pekan (USD)"},
                         title="Kuadran Toko: Skala Penjualan vs Pertumbuhan")
        fig.add_vline(x=0, line_dash="dash", line_color=RED)
        fig.update_traces(textposition="top center")
        show(fig, 480)
        interpretasi(
            "Interpretasi Kelompok",
            "Toko yang berada di kuadran kiri-atas (skala besar namun menurun) merupakan "
            "prioritas audit tertinggi karena potensi kehilangan pendapatan paling besar. "
            "Sebaliknya, toko di kuadran kanan-bawah menawarkan peluang pertumbuhan yang layak "
            "dipelajari dan direplikasi."
        )
    else:
        st.info("Data tidak mencukupi untuk menghitung pertumbuhan (memerlukan minimal dua tahun).")

    divider()
    st.markdown("#### 3) Volatilitas Penjualan per Toko")
    st.caption("CV (coefficient of variation) = simpangan baku dibagi rata-rata. Semakin tinggi "
               "nilai CV, semakin sulit penjualan diprediksi.")

    t = ss.sort_values("CV", ascending=False).copy()
    t["Toko"] = t.Store.astype(int).astype(str)
    fig = px.bar(t, x="Toko", y="CV", color_discrete_sequence=[YELLOW],
                 title="Volatilitas Penjualan per Toko (CV)")
    fig.update_xaxes(type="category")
    show(fig, 340)

    interpretasi(
        "Interpretasi Kelompok",
        "Toko dengan CV tinggi membutuhkan buffer stok dan jadwal tenaga kerja yang lebih "
        "fleksibel, sementara toko dengan CV rendah dapat diterapkan kebijakan lean atau "
        "just-in-time."
    )

    divider()
    st.markdown("#### 4) Tabel Rincian Kinerja Toko")

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

# ============================================================================
# TAB 3 — MUSIMAN & HARI LIBUR
# ============================================================================
with tab3:
    st.markdown("### Pola Musiman dan Dampak Hari Libur")
    st.markdown(
        "Bagian ini mengkaji bagaimana penjualan berfluktuasi sepanjang tahun serta sejauh "
        "mana pekan-pekan libur memberikan dampak berbeda dibanding pekan biasa. Hasil analisis "
        "menjadi dasar penentuan kalender puncak dan realokasi anggaran promosi."
    )

    divider()
    st.markdown("#### 1) Indeks Musiman Bulanan")
    st.caption("Nilai positif menunjukkan penjualan di atas rata-rata keseluruhan; "
               "nilai negatif menunjukkan sebaliknya.")

    si = seasonality(df)
    sdf = pd.DataFrame({"Bulan": [MONTH_ID[m] for m in si.index], "Indeks": si.values * 100,
                        "Arah": np.where(si.values >= 0, "Di atas rata-rata", "Di bawah rata-rata")})
    fig = px.bar(sdf, x="Bulan", y="Indeks", color="Arah",
                 color_discrete_map={"Di atas rata-rata": BLUE, "Di bawah rata-rata": GREY},
                 title="Indeks Musiman Bulanan (Penyimpangan vs Rata-rata, %)")
    show(fig, 360)

    interpretasi(
        "Interpretasi Kelompok",
        "Puncak musiman terkonsentrasi pada November–Desember, sedangkan Januari menjadi "
        "bulan terlemah. Pola ini kami jadikan acuan untuk menyusun kalender pengadaan dan "
        "promosi tahunan."
    )

    divider()
    st.markdown("#### 2) Pola Mingguan per Tahun")
    st.caption("Sumbu X menunjukkan pekan ke-n dalam tahun, sehingga pola antar tahun dapat "
               "dibandingkan secara langsung.")

    w = weekly_table(df)
    w["Tahun"] = w.Year.astype(str)
    fig = px.line(w.sort_values("Week"), x="Week", y="Total", color="Tahun",
                  title="Total Penjualan per Pekan ke-n dalam Tahun",
                  color_discrete_sequence=[BLUE, YELLOW, DARK, RED])
    show(fig, 380)

    divider()
    st.markdown("#### 3) Dampak Hari Libur")
    st.caption("Lift dihitung sebagai selisih relatif pekan libur terhadap pekan non-libur.")

    ev = holiday_events(df)
    hs = holiday_summary(ev)
    if len(hs):
        fig = px.bar(hs.assign(Lift=hs.Lift_Global * 100), x="Event", y="Lift",
                     title="Rata-rata Dampak Pekan Libur vs Pekan Non-Libur (%)",
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

        interpretasi(
            "Interpretasi Kelompok",
            "Thanksgiving tercatat sebagai pekan libur dengan dampak terbesar, sementara "
            "Super Bowl dan Labor Day relatif lemah. Kami menilai realokasi anggaran promosi "
            "dari kedua event terakhir ke pekan Thanksgiving perlu dipertimbangkan."
        )
    else:
        st.info("Tidak terdapat pekan libur pada filter yang dipilih.")

    divider()
    st.markdown("#### 4) Sepuluh Pekan dengan Penjualan Tertinggi")

    top = w.nlargest(10, "Total")[["Date", "Total", "Holiday"]].copy()
    top["Holiday"] = np.where(top.Holiday == 1, "Ya", "Tidak")
    top["Date"] = top.Date.apply(fmt_date)
    table(top, column_config={"Total": st.column_config.NumberColumn("Total ($)", format="$%.0f"),
                              "Holiday": st.column_config.TextColumn("Ditandai libur?")})

    catatan(
        "Pekan puncak sebelum Natal sering tidak ditandai sebagai libur pada kolom "
        "Holiday_Flag. Oleh karena itu, kami menyarankan agar analisis puncak musim tidak "
        "hanya bergantung pada flag tersebut."
    )

# ============================================================================
# TAB 4 — FAKTOR EKSTERNAL
# ============================================================================
with tab4:
    st.markdown("### Pengaruh Faktor Eksternal")
    st.markdown(
        "Bagian ini mengukur sejauh mana faktor makro (suhu, harga BBM, CPI, dan tingkat "
        "pengangguran) berkorelasi dengan penjualan. Tujuannya adalah menilai apakah "
        "faktor-faktor tersebut layak dijadikan pertimbangan utama dalam peramalan."
    )

    drv, dd = driver_table(df)

    divider()
    st.markdown("#### 1) Korelasi Faktor Eksternal dengan Penjualan")
    st.caption("Korelasi Pearson dihitung terhadap penjualan asli maupun terhadap indeks toko "
               "(penjualan yang telah dinormalisasi terhadap rata-rata tokonya).")

    long = drv.melt(id_vars="Faktor", var_name="Metode", value_name="r")
    fig = px.bar(long, x="Faktor", y="r", color="Metode", barmode="group",
                 color_discrete_sequence=[BLUE, YELLOW], title="Koefisien Korelasi Pearson")
    fig.update_yaxes(range=[-1, 1])
    show(fig, 360)

    catatan(
        "Indeks toko = penjualan dibagi rata-rata tokonya, sehingga perbedaan skala antar "
        "toko tidak mengacaukan analisis. Nilai |r| di bawah 0.3 kami kategorikan sebagai "
        "hubungan lemah."
    )

    divider()
    st.markdown("#### 2) Visualisasi Hubungan Faktor Eksternal")

    left, right = st.columns(2)
    with left:
        samp = dd.sample(min(len(dd), 2500), random_state=1)
        fig = px.scatter(samp, x="Unemployment", y="Indeks", opacity=0.35,
                         color_discrete_sequence=[BLUE],
                         title="Pengangguran vs Indeks Penjualan Toko")
        if dd.Unemployment.nunique() > 1:
            k, b = np.polyfit(dd.Unemployment, dd.Indeks, 1)
            xs = np.array([dd.Unemployment.min(), dd.Unemployment.max()])
            fig.add_trace(go.Scatter(x=xs, y=k * xs + b, mode="lines", name="Garis Tren",
                                     line=dict(color=RED, width=3)))
        show(fig, 380)
    with right:
        bins = pd.cut(dd.Temperature, [-20, 40, 60, 80, 120],
                      labels=["<40°F", "40-60°F", "60-80°F", ">80°F"])
        tb = dd.groupby(bins, observed=True).Indeks.mean().reset_index()
        tb.columns = ["Suhu", "Indeks"]
        fig = px.bar(tb, x="Suhu", y="Indeks", color_discrete_sequence=[YELLOW],
                     title="Indeks Penjualan Menurut Rentang Suhu")
        show(fig, 380)

    interpretasi(
        "Interpretasi Kelompok",
        "Nilai korelasi yang rendah menunjukkan bahwa faktor eksternal bukan penentu utama "
        "penjualan. Kami menilai faktor internal—seperti identitas toko dan pekan dalam "
        "tahun—lebih menentukan, sebagaimana akan ditunjukkan pada tab Pusat Keputusan."
    )

    catatan(
        "Suhu berkorelasi dengan musim (Desember dingin sekaligus puncak belanja). "
        "Oleh karena itu, hubungan pada grafik tidak boleh ditafsirkan sebagai hubungan "
        "sebab-akibat."
    )

# ============================================================================
# TAB 5 — PUSAT KEPUTUSAN
# ============================================================================
with tab5:
    st.markdown("### 🎯 Pusat Keputusan")
    st.markdown(
        "Bagian ini merangkum keputusan yang kami usulkan berdasarkan seluruh temuan pada "
        "tab-tab sebelumnya. Setiap keputusan disertai bukti data, usulan tindakan, dan "
        "indikator pemantauan (KPI) agar dapat ditindaklanjuti secara terukur."
    )

    with st.expander("📘 Metodologi Penyusunan Keputusan", expanded=False):
        st.markdown(
            "Rekomendasi disusun melalui tahapan berikut:\n"
            "1. **Klasifikasi ABC** untuk mengelompokkan toko berdasarkan kontribusi penjualan "
            "(Pareto 70%/90%).\n"
            "2. **Analisis pertumbuhan** pada periode yang sebanding (Februari–Oktober) untuk "
            "menghindari bias tahun yang tidak lengkap.\n"
            "3. **Dekomposisi musiman** untuk mengidentifikasi pekan dan bulan puncak.\n"
            "4. **Uji lift hari libur** dengan pembanding global maupun lokal (±4 pekan) agar "
            "dampak tidak dipengaruhi tren musiman.\n"
            "5. **Analisis korelasi** untuk memverifikasi apakah faktor eksternal layak "
            "dijadikan pertimbangan utama.\n\n"
            "Seluruh perhitungan dilakukan pada data lengkap (bukan subset filter) agar "
            "rekomendasi tetap stabil."
        )

    icon = {"Tinggi": "🔴", "Menengah": "🟠", "Rendah": "🟢"}
    decisions = build_decisions(df_all)

    n_hi = sum(d["prio"] == "Tinggi" for d in decisions)
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Keputusan", len(decisions),
              help="Jumlah keputusan yang kami usulkan berdasarkan analisis data.")
    m2.metric("Prioritas Tinggi", n_hi,
              help="Keputusan yang perlu segera ditindaklanjuti.")
    m3.metric("Area Tercakup", len({d["area"] for d in decisions}),
              help="Banyaknya area fungsional yang tercakup dalam rekomendasi.")

    divider()
    st.markdown("#### Rincian Keputusan dan Usulan Tindakan")

    for i, d in enumerate(decisions, 1):
        with st.container(border=True):
            st.markdown(f"**{icon[d['prio']]} Keputusan {i} — {d['keputusan']}**")
            st.caption(f"Prioritas: {d['prio']}  ·  Area: {d['area']}")
            st.markdown(f"**Bukti Data:** {d['bukti']}")
            st.markdown("**Usulan Tindakan:**\n" + "\n".join(f"- {a}" for a in d["aksi"]))
            st.markdown(f"**KPI Pemantauan:** {d['kpi']}")

    divider()
    st.markdown("#### Rekomendasi Tindakan per Toko")
    st.caption("Rekomendasi dihasilkan dari kombinasi kelas ABC dan pertumbuhan terakhir masing-masing toko.")

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
    st.download_button("⬇️ Unduh Rekomendasi per Toko (CSV)",
                       acts.to_csv(index=False).encode("utf-8"),
                       file_name="rekomendasi_toko.csv", mime="text/csv")

    divider()
    st.markdown("#### 🧮 Simulasi Dampak Keputusan (What-If)")
    st.markdown(
        "Simulasi berikut memberikan gambaran skala dampak apabila keputusan yang kami "
        "usulkan dijalankan. Perlu ditegaskan bahwa simulasi ini mengukur **pendapatan**, "
        "bukan laba, karena dataset tidak memuat informasi biaya atau margin."
    )

    s1, s2 = st.columns(2)
    up = s1.slider("Kenaikan penjualan Nov–Des dari kesiapan stok dan staf yang lebih baik (%)",
                   min_value=0.0, max_value=10.0, value=3.0, step=0.5)
    rec = s2.slider("Persentase penurunan toko yang berhasil dipulihkan (%)",
                    min_value=0, max_value=100, value=50, step=5)
    peak_rev, peak_gain, gap, gap_gain = simulate(df_all, up / 100, rec / 100)
    r1, r2, r3 = st.columns(3)
    r1.metric("Pendapatan Nov–Des (per tahun)", fmt_usd(peak_rev),
              help="Rata-rata pendapatan November–Desember pada tahun-tahun dengan data lengkap.")
    r2.metric("Tambahan dari Kesiapan Musim Puncak", fmt_usd(peak_gain),
              help="Estimasi tambahan pendapatan dari kesiapan stok dan staf pada puncak musim.")
    r3.metric("Tambahan dari Pemulihan Toko Menurun", fmt_usd(gap_gain),
              help=f"Selisih tahunan penjualan toko menurun terhadap tahun sebelumnya: {fmt_usd(gap)}")

    interpretasi(
        "Interpretasi Kelompok",
        "Angka simulasi di atas kami sajikan sebagai gambaran skala prioritas, bukan sebagai "
        "ramalan. Tujuannya adalah membantu pemangku kepentingan memahami besaran dampak "
        "relatif antar keputusan, sehingga alokasi perhatian dan sumber daya dapat "
        "diprioritaskan secara lebih rasional."
    )

    divider()
    st.markdown("#### Kesimpulan Kelompok")
    st.markdown(
        "Berdasarkan seluruh analisis, kelompok kami menyimpulkan bahwa **prioritas utama "
        "terletak pada pengelolaan musim puncak (Thanksgiving dan Desember), perlindungan "
        "toko kelas A, serta pemulihan toko yang menurun**. Faktor eksternal seperti suhu "
        "dan pengangguran kami nilai sebagai sinyal pendukung, bukan penentu utama. "
        "Rekomendasi ini bersifat indikatif dan sebaiknya dilengkapi dengan data biaya, "
        "margin, dan konteks operasional sebelum diimplementasikan secara penuh."
    )
