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
