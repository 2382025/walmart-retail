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

# ==========================================
# 4. JUDUL DASBOR
# ==========================================

st.title("Dasbor Analisis Penjualan Walmart")
st.write(
    "Dasbor ini menyajikan informasi penjualan, kinerja toko, "
    "tren penjualan, faktor ekonomi, dan rekomendasi keputusan bisnis."
)

st.caption(
    f"Periode data yang ditampilkan: {data['Date'].min().date()} "
    f"sampai {data['Date'].max().date()}"
)

# ==========================================
# 5. NAVIGASI TAB
# ==========================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Ringkasan",
    "Kinerja Toko",
    "Tren Penjualan",
    "Analisis Ekonomi",
    "Pengambilan Keputusan"
])

# ==========================================
# TAB 1: RINGKASAN
# ==========================================

with tab1:
    st.subheader("Ringkasan Penjualan")

    total_penjualan = data["Weekly_Sales"].sum()
    rata_rata_penjualan = data["Weekly_Sales"].mean()
    penjualan_tertinggi = data["Weekly_Sales"].max()
    jumlah_toko = data["Store"].nunique()

    kolom1, kolom2, kolom3, kolom4 = st.columns(4)

    kolom1.metric("Total Penjualan", f"${total_penjualan:,.0f}")
    kolom2.metric("Rata-rata Penjualan Mingguan", f"${rata_rata_penjualan:,.0f}")
    kolom3.metric("Penjualan Mingguan Tertinggi", f"${penjualan_tertinggi:,.0f}")
    kolom4.metric("Jumlah Toko", jumlah_toko)

    st.divider()
    st.subheader("Tren Total Penjualan Bulanan")

    penjualan_bulanan = (
        data.groupby(data["Date"].dt.to_period("M"))["Weekly_Sales"]
        .sum()
        .reset_index()
    )
    penjualan_bulanan["Bulan"] = penjualan_bulanan["Date"].astype(str)

    grafik_bulanan = px.line(
        penjualan_bulanan,
        x="Bulan",
        y="Weekly_Sales",
        markers=True,
        title="Total Penjualan Setiap Bulan",
        labels={
            "Bulan": "Bulan",
            "Weekly_Sales": "Total Penjualan ($)"
        }
    )

    st.plotly_chart(grafik_bulanan, use_container_width=True)

# ==========================================
# TAB 2: KINERJA TOKO
# ==========================================

with tab2:
    st.subheader("Analisis Kinerja Setiap Toko")

    penjualan_toko = (
        data.groupby("Store")["Weekly_Sales"]
        .agg(["sum", "mean"])
        .reset_index()
    )

    penjualan_toko.columns = [
        "Nomor Toko",
        "Total Penjualan",
        "Rata-rata Penjualan Mingguan"
    ]

    penjualan_toko = penjualan_toko.sort_values(
        "Total Penjualan",
        ascending=False
    )

    grafik_toko = px.bar(
        penjualan_toko,
        x="Nomor Toko",
        y="Total Penjualan",
        color="Total Penjualan",
        title="Total Penjualan Berdasarkan Toko",
        color_continuous_scale="Blues",
        labels={"Total Penjualan": "Total Penjualan ($)"}
    )

    st.plotly_chart(grafik_toko, use_container_width=True)

    st.subheader("Peringkat Penjualan Toko")
    st.dataframe(
        penjualan_toko.style.format({
            "Total Penjualan": "${:,.2f}",
            "Rata-rata Penjualan Mingguan": "${:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

# ==========================================
# TAB 3: TREN PENJUALAN
# ==========================================

with tab3:
    st.subheader("Tren Penjualan Mingguan")

    penjualan_mingguan = (
        data.groupby("Date")["Weekly_Sales"]
        .sum()
        .reset_index()
    )

    grafik_mingguan = px.line(
        penjualan_mingguan,
        x="Date",
        y="Weekly_Sales",
        title="Total Penjualan Setiap Minggu",
        markers=True,
        labels={
            "Date": "Tanggal",
            "Weekly_Sales": "Total Penjualan ($)"
        }
    )

    st.plotly_chart(grafik_mingguan, use_container_width=True)

    st.divider()
    st.subheader("Perbandingan Penjualan Hari Libur dan Hari Biasa")

    if "Holiday_Flag" in data.columns:
        data_libur = (
            data.groupby("Holiday_Flag")["Weekly_Sales"]
            .mean()
            .reset_index()
        )

        data_libur["Jenis Periode"] = data_libur["Holiday_Flag"].map({
            0: "Minggu Biasa",
            1: "Minggu Hari Libur"
        })

        grafik_libur = px.bar(
            data_libur,
            x="Jenis Periode",
            y="Weekly_Sales",
            color="Jenis Periode",
            title="Rata-rata Penjualan: Minggu Biasa dan Hari Libur",
            labels={
                "Jenis Periode": "Jenis Periode",
                "Weekly_Sales": "Rata-rata Penjualan ($)"
            }
        )

        st.plotly_chart(grafik_libur, use_container_width=True)

        if 0 in data_libur["Holiday_Flag"].values and 1 in data_libur["Holiday_Flag"].values:
            rata_biasa = data_libur.loc[
                data_libur["Holiday_Flag"] == 0, "Weekly_Sales"
            ].iloc[0]

            rata_libur = data_libur.loc[
                data_libur["Holiday_Flag"] == 1, "Weekly_Sales"
            ].iloc[0]

            selisih_libur = ((rata_libur - rata_biasa) / rata_biasa) * 100

            st.metric(
                "Perbedaan Rata-rata Penjualan",
                f"{selisih_libur:+.2f}%",
                help="Persentase perbedaan rata-rata penjualan minggu hari libur dibandingkan minggu biasa."
            )
        else:
            st.info("Data minggu libur dan minggu biasa belum lengkap untuk dibandingkan pada penyaringan ini.")
    else:
        st.info("Kolom penanda hari libur tidak tersedia dalam data.")

# ==========================================
# TAB 4: ANALISIS EKONOMI
# ==========================================

with tab4:
    st.subheader("Analisis Faktor Ekonomi")

    kolom_ekonomi = [
        "Weekly_Sales",
        "Temperature",
        "Fuel_Price",
        "CPI",
        "Unemployment"
    ]

    kolom_tersedia = [
        kolom for kolom in kolom_ekonomi
        if kolom in data.columns
    ]

    if len(kolom_tersedia) >= 2:
        korelasi = data[kolom_tersedia].corr(numeric_only=True)

        grafik_korelasi = px.imshow(
            korelasi,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            title="Hubungan antara Penjualan dan Faktor Ekonomi",
            aspect="auto"
        )

        st.plotly_chart(grafik_korelasi, use_container_width=True)

        st.info(
            "Korelasi menunjukkan tingkat hubungan antarvariabel, "
            "bukan bukti bahwa satu variabel menyebabkan perubahan pada variabel lain."
        )
    else:
        st.info("Data faktor ekonomi belum cukup untuk menampilkan analisis korelasi.")

# ==========================================
# TAB 5: PENGAMBILAN KEPUTUSAN
# ==========================================

with tab5:
    st.header("Pengambilan Keputusan")
    st.write(
        "Bagian ini menyajikan keputusan dan langkah yang dapat dilakukan "
        "manajemen berdasarkan hasil analisis data penjualan."
    )

    # ------------------------------------------
    # KEPUTUSAN 1: EVALUASI KINERJA TOKO
    # ------------------------------------------

    st.subheader("1. Evaluasi Kinerja Toko")

    rata_penjualan_toko = (
        data.groupby("Store")["Weekly_Sales"]
        .mean()
        .reset_index()
    )

    rata_penjualan_toko.columns = ["Nomor Toko", "Rata-rata Penjualan Mingguan"]

    rata_keseluruhan = data["Weekly_Sales"].mean()

    rata_penjualan_toko["Status"] = np.where(
        rata_penjualan_toko["Rata-rata Penjualan Mingguan"] >= rata_keseluruhan,
        "Di Atas Rata-rata",
        "Di Bawah Rata-rata"
    )

    toko_di_bawah = rata_penjualan_toko[
        rata_penjualan_toko["Status"] == "Di Bawah Rata-rata"
    ]

    toko_di_atas = rata_penjualan_toko[
        rata_penjualan_toko["Status"] == "Di Atas Rata-rata"
    ]

    kolom1, kolom2 = st.columns(2)
    kolom1.metric("Toko di Atas Rata-rata", len(toko_di_atas))
    kolom2.metric("Toko di Bawah Rata-rata", len(toko_di_bawah))

    grafik_status_toko = px.bar(
        rata_penjualan_toko,
        x="Nomor Toko",
        y="Rata-rata Penjualan Mingguan",
        color="Status",
        title="Rata-rata Penjualan Mingguan Setiap Toko",
        labels={
            "Rata-rata Penjualan Mingguan": "Rata-rata Penjualan ($)"
        },
        color_discrete_map={
            "Di Atas Rata-rata": "#2E8B57",
            "Di Bawah Rata-rata": "#E09F3E"
        }
    )

    st.plotly_chart(grafik_status_toko, use_container_width=True)

    toko_total = (
        data.groupby("Store")["Weekly_Sales"]
        .sum()
        .reset_index()
        .sort_values("Weekly_Sales", ascending=False)
    )

    toko_tertinggi = toko_total.iloc[0]
    toko_terendah = toko_total.iloc[-1]

    kolom1, kolom2 = st.columns(2)

    kolom1.metric(
        "Total Penjualan Tertinggi",
        f"Toko {int(toko_tertinggi['Store'])}",
        f"${toko_tertinggi['Weekly_Sales']:,.0f}"
    )

    kolom2.metric(
        "Total Penjualan Terendah",
        f"Toko {int(toko_terendah['Store'])}",
        f"${toko_terendah['Weekly_Sales']:,.0f}"
    )

    st.markdown("**Keputusan:**")
    st.write(
        "Manajemen perlu mengevaluasi toko yang memiliki rata-rata penjualan "
        "di bawah rata-rata keseluruhan. Toko dengan penjualan tinggi dapat "
        "dijadikan bahan pembelajaran untuk membandingkan strategi dan kinerjanya."
    )

    st.markdown("**Langkah yang dapat dilakukan:**")
    st.write("""
    - Mencari tahu penyebab rendahnya penjualan pada toko tertentu.
    - Membandingkan kinerja toko yang penjualannya tinggi dan rendah.
    - Menyusun rencana peningkatan penjualan untuk toko yang perlu dievaluasi.
    """)

    st.caption(
        "Catatan: Penjualan rendah belum tentu berarti kinerja toko buruk. "
        "Ukuran toko, lokasi, jumlah pelanggan, dan biaya operasional tidak tersedia dalam data ini."
    )

    # ------------------------------------------
    # KEPUTUSAN 2: STRATEGI HARI LIBUR
    # ------------------------------------------

    st.divider()
    st.subheader("2. Strategi Penjualan pada Hari Libur")

    if "Holiday_Flag" in data.columns:
        hasil_libur = data.groupby("Holiday_Flag")["Weekly_Sales"].mean()

        if 0 in hasil_libur.index and 1 in hasil_libur.index:
            rata_biasa = hasil_libur.loc[0]
            rata_libur = hasil_libur.loc[1]

            persentase_libur = (
                (rata_libur - rata_biasa) / rata_biasa * 100
                if rata_biasa != 0 else 0
            )

            kolom1, kolom2, kolom3 = st.columns(3)
            kolom1.metric("Rata-rata Minggu Biasa", f"${rata_biasa:,.0f}")
            kolom2.metric("Rata-rata Minggu Hari Libur", f"${rata_libur:,.0f}")
            kolom3.metric("Perbedaan Penjualan", f"{persentase_libur:+.2f}%")

            st.markdown("**Keputusan:**")
            if persentase_libur > 0:
                st.write(
                    "Rata-rata penjualan pada minggu hari libur lebih tinggi "
                    "dibandingkan minggu biasa. Perusahaan dapat mempersiapkan "
                    "kegiatan operasional dan promosi menjelang periode hari libur."
                )
            else:
                st.write(
                    "Rata-rata penjualan pada minggu hari libur tidak lebih tinggi "
                    "dibandingkan minggu biasa. Perusahaan perlu mengevaluasi "
                    "strategi penjualan pada periode tersebut."
                )

            st.markdown("**Langkah yang dapat dilakukan:**")
            st.write("""
            - Mempersiapkan tenaga kerja sebelum periode hari libur.
            - Merencanakan promosi pada periode hari libur.
            - Mengevaluasi hasil penjualan setelah periode hari libur.
            """)
        else:
            st.info(
                "Data minggu hari libur dan minggu biasa belum lengkap "
                "untuk dibandingkan pada penyaringan saat ini."
            )

    # ------------------------------------------
    # KEPUTUSAN 3: STRATEGI PENJUALAN BULANAN
    # ------------------------------------------

    st.divider()
    st.subheader("3. Strategi Penjualan Berdasarkan Bulan")

    nama_bulan = {
        1: "Januari", 2: "Februari", 3: "Maret",
        4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September",
        10: "Oktober", 11: "November", 12: "Desember"
    }

    penjualan_bulanan_dm = (
        data.groupby(data["Date"].dt.month)["Weekly_Sales"]
        .mean()
        .sort_values(ascending=False)
    )

    if not penjualan_bulanan_dm.empty:
        bulan_tertinggi = penjualan_bulanan_dm.idxmax()
        bulan_terendah = penjualan_bulanan_dm.idxmin()

        kolom1, kolom2 = st.columns(2)

        kolom1.metric(
            "Bulan dengan Penjualan Tertinggi",
            nama_bulan[bulan_tertinggi],
            f"${penjualan_bulanan_dm.max():,.0f}"
        )

        kolom2.metric(
            "Bulan dengan Penjualan Terendah",
            nama_bulan[bulan_terendah],
            f"${penjualan_bulanan_dm.min():,.0f}"
        )

        st.markdown("**Keputusan:**")
        st.write(
            "Perusahaan dapat memanfaatkan bulan dengan penjualan tinggi "
            "untuk meningkatkan kesiapan operasional. Pada bulan dengan "
            "penjualan rendah, perusahaan dapat meningkatkan kegiatan pemasaran."
        )

        st.markdown("**Langkah yang dapat dilakukan:**")
        st.write("""
        - Mempersiapkan promosi sebelum bulan dengan penjualan tinggi.
        - Mengevaluasi penyebab penurunan penjualan pada bulan tertentu.
        - Menyesuaikan strategi pemasaran berdasarkan pola penjualan bulanan.
        """)

    # ------------------------------------------
    # KEPUTUSAN 4: PENETAPAN TARGET PENJUALAN
    # ------------------------------------------

    st.divider()
    st.subheader("4. Penetapan Target Penjualan Setiap Toko")

    persentase_target = st.slider(
        "Pilih Target Peningkatan Penjualan (%)",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        key="target_penjualan_dm"
    )

    target_toko = rata_penjualan_toko.copy()

    target_toko["Target Penjualan Mingguan"] = (
        target_toko["Rata-rata Penjualan Mingguan"]
        * (1 + persentase_target / 100)
    )

    target_toko["Tambahan Penjualan"] = (
        target_toko["Target Penjualan Mingguan"]
        - target_toko["Rata-rata Penjualan Mingguan"]
    )

    st.write(
        f"Simulasi target peningkatan penjualan sebesar **{persentase_target}%** "
        "dari rata-rata penjualan mingguan setiap toko."
    )

    st.dataframe(
        target_toko.style.format({
            "Rata-rata Penjualan Mingguan": "${:,.2f}",
            "Target Penjualan Mingguan": "${:,.2f}",
            "Tambahan Penjualan": "${:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("**Keputusan:**")
    st.write(
        "Perusahaan dapat menetapkan target peningkatan penjualan untuk "
        "setiap toko berdasarkan rata-rata penjualan sebelumnya. Target "
        "tersebut dapat digunakan untuk memantau perkembangan kinerja toko."
    )

    st.markdown("**Langkah yang dapat dilakukan:**")
    st.write("""
    - Menentukan target penjualan untuk setiap toko.
    - Membandingkan hasil penjualan dengan target yang telah ditentukan.
    - Mengevaluasi toko yang belum mencapai target.
    """)

    st.caption(
        "Target ini merupakan simulasi berdasarkan persentase yang dipilih, "
        "bukan hasil prediksi penjualan."
    )

    # ------------------------------------------
    # KEPUTUSAN 5: FAKTOR EKONOMI
    # ------------------------------------------

    st.divider()
    st.subheader("5. Mempertimbangkan Faktor Ekonomi")

    faktor_ekonomi = [
        "Temperature",
        "Fuel_Price",
        "CPI",
        "Unemployment"
    ]

    faktor_tersedia = [
        kolom for kolom in faktor_ekonomi
        if kolom in data.columns
    ]

    if faktor_tersedia:
        hasil_korelasi = (
            data[faktor_tersedia + ["Weekly_Sales"]]
            .corr(numeric_only=True)["Weekly_Sales"]
            .drop("Weekly_Sales")
        )

        tabel_korelasi = hasil_korelasi.reset_index()
        tabel_korelasi.columns = [
            "Faktor Ekonomi",
            "Hubungan dengan Penjualan"
        ]

        nama_faktor = {
            "Temperature": "Suhu",
            "Fuel_Price": "Harga Bahan Bakar",
            "CPI": "Indeks Harga Konsumen",
            "Unemployment": "Tingkat Pengangguran"
        }

        tabel_korelasi["Faktor Ekonomi"] = (
            tabel_korelasi["Faktor Ekonomi"].map(nama_faktor)
        )

        st.dataframe(
            tabel_korelasi.style.format({
                "Hubungan dengan Penjualan": "{:.3f}"
            }),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("**Keputusan:**")
        st.write(
            "Faktor ekonomi tidak sebaiknya digunakan sebagai satu-satunya "
            "dasar dalam menentukan strategi penjualan karena hubungan "
            "korelasinya dengan penjualan pada data ini relatif lemah."
        )

        st.markdown("**Langkah yang dapat dilakukan:**")
        st.write("""
        - Tetap memperhatikan perubahan kondisi ekonomi.
        - Menggabungkan informasi ekonomi dengan pola penjualan.
        - Mempertimbangkan faktor lain seperti promosi dan kebutuhan pelanggan.
        """)

        st.caption(
            "Nilai korelasi menunjukkan hubungan, bukan sebab-akibat."
        )
    else:
        st.info("Kolom faktor ekonomi tidak tersedia dalam data.")

    # ------------------------------------------
    # RINGKASAN KEPUTUSAN
    # ------------------------------------------

    st.divider()
    st.subheader("Ringkasan Keputusan")

    ringkasan_keputusan = pd.DataFrame({
        "Hasil Analisis": [
            "Kinerja toko",
            "Penjualan hari libur",
            "Penjualan bulanan",
            "Target penjualan",
            "Faktor ekonomi"
        ],
        "Keputusan": [
            "Mengevaluasi toko dengan penjualan rendah",
            "Mempersiapkan operasional menjelang hari libur",
            "Menyusun strategi pemasaran berdasarkan bulan",
            "Menetapkan target penjualan setiap toko",
            "Memantau perubahan faktor ekonomi"
        ],
        "Tujuan": [
            "Meningkatkan kinerja toko",
            "Memanfaatkan peluang penjualan hari libur",
            "Mengoptimalkan penjualan setiap bulan",
            "Memantau perkembangan penjualan",
            "Mendukung pengambilan keputusan"
        ]
    })

    st.dataframe(
        ringkasan_keputusan,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Catatan: Rekomendasi dibuat berdasarkan data historis penjualan "
        "Walmart tahun 2010–2012. Rekomendasi ini merupakan usulan berdasarkan "
        "hasil analisis, bukan bukti bahwa Walmart benar-benar menerapkannya."
    )

    # ------------------------------------------
    # UNDUH DATA
    # ------------------------------------------

    st.divider()
    st.subheader("Unduh Data Analisis")

    st.download_button(
        "Unduh Data CSV",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="Walmart_Filtered.csv",
        mime="text/csv"
    )

# ==========================================
# 6. KAKI HALAMAN
# ==========================================

st.sidebar.divider()
st.sidebar.caption("Proyek Business Intelligence | Walmart Retail")
