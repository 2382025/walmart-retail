
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
    tg_lift = hs_val("Thanksgiving", "Lift_Global")
    tg_loc = hs_val("Thanksgiving", "Lift_Local")
    tg_sales = hs_val("Thanksgiving", "Rata2_Toko")

    if pd.notna(tg_lift):
        D.append(dict(
            prio="Tinggi",
            area="Persediaan Barang & Tenaga Kerja",
            keputusan=(
                "Thanksgiving perlu menjadi salah satu fokus utama dalam "
                "persiapan stok barang dan pengaturan jadwal karyawan."
            ),
            bukti=(
                f"Berdasarkan data, rata-rata penjualan per toko pada pekan "
                f"Thanksgiving mencapai {fmt_usd(tg_sales, 2)}. Angka ini "
                f"{pct(tg_lift, 0, False)} lebih tinggi dibandingkan pekan "
                f"biasa dan {pct(tg_loc, 0, False)} lebih tinggi dibandingkan "
                f"rata-rata empat pekan di sekitarnya. Pola tersebut juga "
                f"terlihat pada {int(hs_val('Thanksgiving', 'N'))} pekan "
                f"Thanksgiving selama periode pengamatan."
            ),
            aksi=[
                "Stok untuk produk yang banyak diminati sebaiknya mulai disiapkan sekitar 3–4 pekan sebelum Thanksgiving.",
                "Jadwal karyawan dan kasir tambahan perlu diatur lebih awal untuk mengantisipasi peningkatan jumlah pembeli.",
                "Anggaran promosi dapat lebih difokuskan pada periode Thanksgiving karena peningkatan penjualannya lebih terlihat."
            ],
            kpi=(
                "Jumlah barang yang kehabisan stok, tingkat ketersediaan produk, "
                "dan perbandingan penjualan Thanksgiving setiap tahun."
            )
        ))

    # 2 — Puncak Natal dan pekan sebelum Natal
    dec_idx = si.get(12, np.nan)
    top = w.nlargest(5, "Total")
    unflag = top[top.Holiday == 0]

    if pd.notna(dec_idx):
        top_txt = (
            ", ".join(
                f"{fmt_date(d)} ({fmt_usd(t)})"
                for d, t in zip(top.Date, top.Total)
            ) if len(top) else "-"
        )

        D.append(dict(
            prio="Tinggi",
            area="Persiapan Musim Penjualan",
            keputusan=(
                "Periode menjelang Natal perlu dimasukkan ke dalam "
                "perencanaan musim penjualan, meskipun tidak seluruh "
                "pekannya tercatat sebagai hari libur pada Holiday_Flag."
            ),
            bukti=(
                f"Penjualan pada bulan Desember tercatat "
                f"{pct(dec_idx, 0, False)} di atas rata-rata keseluruhan. "
                f"Beberapa pekan dengan penjualan tertinggi adalah {top_txt}. "
                f"Dari lima pekan dengan penjualan tertinggi, {len(unflag)} "
                f"pekan tidak memiliki tanda hari libur. Hal ini menunjukkan "
                f"bahwa peningkatan penjualan tidak hanya terjadi pada hari "
                f"libur, tetapi juga pada periode menjelang Natal."
            ),
            aksi=[
                "Menambahkan periode pra-Natal (pekan ketiga dan keempat Desember) sebagai salah satu periode khusus dalam perencanaan penjualan.",
                "Persiapan stok, gudang, transportasi, dan kebutuhan karyawan sebaiknya mulai dilakukan sejak awal November.",
                "Menyediakan stok cadangan untuk toko kelas A sebelum memasuki pertengahan Desember."
            ],
            kpi=(
                "Ketersediaan barang selama pra-Natal, jumlah lembur karyawan, "
                "dan penjualan masing-masing toko."
            )
        ))

    # 3 — Januari dan periode setelah Natal
    jan_idx = si.get(1, np.nan)
    ny = hs_val("Natal / Akhir Tahun (pekan 30-31 Des)", "Lift_Global")

    if pd.notna(jan_idx):
        D.append(dict(
            prio="Menengah",
            area="Efisiensi Biaya",
            keputusan=(
                "Setelah periode Natal dan akhir tahun, jumlah stok serta "
                "kebutuhan tenaga kerja perlu disesuaikan dengan kondisi "
                "penjualan yang cenderung lebih rendah pada bulan Januari."
            ),
            bukti=(
                f"Penjualan bulan Januari tercatat {pct(abs(jan_idx), 0, False)} "
                f"di bawah rata-rata keseluruhan"
                f"{' dan menjadi bulan dengan penjualan terendah' if jan_idx == si.min() else ''}. "
                f"Sementara itu, penjualan pada pekan 30–31 Desember tercatat "
                f"{pct(ny, 0)} dibandingkan pekan biasa. Kondisi ini menunjukkan "
                f"bahwa kebutuhan stok dan operasional perlu disesuaikan "
                f"setelah periode penjualan akhir tahun."
            ),
            aksi=[
                "Mengadakan promo untuk menghabiskan sisa stok produk musiman setelah Natal.",
                "Jumlah pemesanan barang pada Januari sebaiknya disesuaikan dengan pola penjualan yang lebih rendah.",
                "Memanfaatkan periode Januari untuk pelatihan karyawan, perawatan, dan perbaikan fasilitas toko."
            ],
            kpi=(
                "Perputaran persediaan, biaya tenaga kerja dibandingkan penjualan, "
                "dan jumlah sisa stok musiman."
            )
        ))

    # 4 — Prioritas untuk toko kelas A
    nA = int((ss.Kelas == "A").sum())
    shareA = ss.loc[ss.Kelas == "A", "Share"].sum()
    top5 = ss.head(5)

    D.append(dict(
        prio="Tinggi",
        area="Pembagian Sumber Daya",
        keputusan=(
            "Toko kelas A perlu mendapatkan perhatian lebih dalam "
            "pembagian stok, tenaga kerja, dan sumber daya operasional "
            "karena memberikan kontribusi penjualan terbesar."
        ),
        bukti=(
            f"Dari hasil analisis ABC, terdapat {nA} dari {len(ss)} toko "
            f"yang masuk kelas A dengan kontribusi sebesar "
            f"{pct(shareA, 0, False)} dari total penjualan. Lima toko "
            f"dengan penjualan tertinggi, yaitu "
            f"{', '.join('Toko ' + str(int(s)) for s in top5.Store)}, "
            f"menyumbang {pct(top5.Share.sum(), 1, False)}. "
            f"Sebagai perbandingan, sepuluh toko dengan penjualan terendah "
            f"hanya menyumbang {pct(ss.tail(10).Share.sum(), 1, False)}."
        ),
        aksi=[
            "Memastikan ketersediaan stok produk pada toko kelas A tetap terjaga.",
            "Ketika stok terbatas, kebutuhan toko kelas A dapat diprioritaskan berdasarkan kontribusi penjualannya.",
            "Melakukan pemantauan penjualan toko kelas A secara rutin agar penurunan kinerja dapat diketahui lebih awal."
        ],
        kpi=(
            "Total penjualan toko kelas A, jumlah barang yang kehabisan stok, "
            "dan tingkat kepuasan pelanggan."
        )
    ))

    # 5 — Toko yang mengalami penurunan penjualan
    dec = gr[gr.G_last < 0]

    if len(gr.dropna(subset=["G_last"])):
        bigA = dec.merge(ss[["Store", "Kelas"]], on="Store")
        bigA = bigA[bigA.Kelas.isin(["A", "B"])]
        two = gr[(gr.G_last < 0) & (gr.G_prev < 0)]

        D.append(dict(
            prio="Tinggi",
            area="Evaluasi Kinerja Toko",
            keputusan=(
                "Toko yang mengalami penurunan penjualan perlu dievaluasi, "
                "terutama toko dengan kontribusi penjualan besar atau yang "
                "mengalami penurunan selama dua tahun berturut-turut."
            ),
            bukti=(
                f"Pada perbandingan periode Februari–Oktober, terdapat "
                f"{len(dec)} dari {len(gr)} toko yang mengalami penurunan "
                f"penjualan pada {y_last} dibandingkan {y_prev}. "
                f"Penurunan terbesar terjadi pada {store_list(gr, 4, True, ss)}. "
                f"Selain itu, terdapat {len(two)} toko yang mengalami "
                f"penurunan selama dua tahun berturut-turut"
                f"{' (' + ', '.join('Toko ' + str(int(s)) for s in two.Store) + ')' if len(two) else ''}. "
                f"Dari jumlah tersebut, {len(bigA)} toko termasuk kelas A atau B, "
                f"sehingga penurunannya perlu mendapat perhatian lebih."
            ),
            aksi=[
                "Memeriksa kemungkinan penyebab penurunan, seperti ketersediaan barang, variasi produk, harga pesaing, dan kondisi lingkungan sekitar toko.",
                "Membandingkan kondisi toko yang mengalami penurunan dengan toko lain yang memiliki karakteristik serupa tetapi penjualannya meningkat.",
                "Menetapkan target perbaikan secara bertahap dan mengevaluasi perkembangannya setiap bulan."
            ],
            kpi=(
                "Pertumbuhan penjualan setiap toko, jumlah pengunjung, "
                "dan ketersediaan barang."
            )
        ))

    # 6 — Toko dengan pertumbuhan penjualan tertinggi
    if len(gr.dropna(subset=["G_last"])):
        D.append(dict(
            prio="Menengah",
            area="Pengembangan Penjualan",
            keputusan=(
                "Toko dengan pertumbuhan penjualan tertinggi dapat dijadikan "
                "contoh untuk melihat strategi yang berpotensi diterapkan "
                "pada toko lain dengan kondisi serupa."
            ),
            bukti=(
                f"Pertumbuhan penjualan tertinggi ditemukan pada "
                f"{store_list(gr, 5, False, ss)}. Sebagian besar toko tersebut "
                f"berada pada kelas B atau C, yang memiliki kontribusi "
                f"penjualan lebih kecil dibandingkan toko kelas A. "
                f"Hasil ini dapat menjadi bahan pertimbangan untuk mencari "
                f"peluang peningkatan penjualan pada toko lainnya."
            ),
            aksi=[
                "Mempelajari hal-hal yang mendukung peningkatan penjualan, seperti variasi produk, promosi, lokasi, dan pengelolaan toko.",
                "Mencoba strategi yang dinilai berhasil pada toko lain dengan kondisi yang relatif sama.",
                "Mempertimbangkan penambahan stok atau kapasitas rak apabila peningkatan permintaan terus berlanjut."
            ],
            kpi=(
                "Perubahan penjualan toko setelah penerapan strategi "
                "dibandingkan dengan toko yang tidak menerapkannya."
            )
        ))

    # 7 — Evaluasi toko kelas C
    c = ss[ss.Kelas == "C"]

    if len(c):
        D.append(dict(
            prio="Menengah",
            area="Efisiensi Biaya",
            keputusan=(
                "Kinerja toko kelas C perlu ditinjau kembali, khususnya "
                "dari sisi penggunaan biaya operasional dan penyesuaian "
                "produk yang dijual, sebelum dilakukan penambahan investasi."
            ),
            bukti=(
                f"Terdapat {len(c)} toko yang masuk kelas C dengan kontribusi "
                f"sebesar {pct(c.Share.sum(), 1, False)} dari total penjualan. "
                f"Beberapa toko dengan penjualan terendah adalah "
                f"{', '.join('Toko ' + str(int(s)) for s in c.tail(3).Store)}. "
                f"Rata-rata penjualan mingguan terendah pada kelompok ini "
                f"adalah {fmt_usd(c.Rata2.min())}."
            ),
            aksi=[
                "Melakukan perhitungan biaya operasional dan margin keuntungan setiap toko sebelum menentukan langkah selanjutnya.",
                "Menyesuaikan jenis dan jumlah produk serta jam operasional dengan kebutuhan pelanggan di sekitar toko.",
                "Tidak langsung mengambil keputusan untuk menutup toko hanya berdasarkan rendahnya angka penjualan."
            ],
            kpi=(
                "Margin keuntungan setiap toko dan perbandingan biaya "
                "operasional terhadap penjualan."
            )
        ))

    # 8 — Perbedaan fluktuasi penjualan antar toko
    hi, lo = ss.nlargest(4, "CV"), ss.nsmallest(4, "CV")

    D.append(dict(
        prio="Menengah",
        area="Pengelolaan Stok",
        keputusan=(
            "Pengelolaan stok sebaiknya disesuaikan dengan pola penjualan "
            "masing-masing toko. Toko dengan penjualan yang sering berubah "
            "membutuhkan stok cadangan lebih fleksibel, sedangkan toko "
            "dengan penjualan stabil dapat menggunakan pengaturan stok "
            "yang lebih efisien."
        ),
        bukti=(
            f"Berdasarkan nilai koefisien variasi (CV), toko dengan "
            f"fluktuasi penjualan tertinggi adalah "
            f"{', '.join(f'Toko {int(r.Store)} ({r.CV:.2f})' for _, r in hi.iterrows())}. "
            f"Sementara itu, toko dengan penjualan paling stabil adalah "
            f"{', '.join(f'Toko {int(r.Store)} ({r.CV:.2f})' for _, r in lo.iterrows())}."
        ),
        aksi=[
            "Menyiapkan stok cadangan dan memperbarui perkiraan permintaan secara rutin untuk toko dengan fluktuasi tinggi.",
            "Menerapkan pengaturan pemesanan stok yang lebih efisien pada toko dengan pola penjualan stabil.",
            "Menyesuaikan jadwal karyawan dengan perubahan kebutuhan operasional masing-masing toko."
        ],
        kpi=(
            "Akurasi perkiraan penjualan (MAPE), jumlah barang yang kehabisan stok, "
            "dan jumlah stok berlebih."
        )
    ))

    # 9 — Evaluasi promosi pada hari libur
    sb = hs_val("Super Bowl", "Lift_Global")
    lb = hs_val("Labor Day", "Lift_Global")

    if pd.notna(sb) or pd.notna(lb):
        D.append(dict(
            prio="Menengah",
            area="Promosi & Pemasaran",
            keputusan=(
                "Anggaran promosi perlu lebih diperhatikan pembagiannya. "
                "Promosi pada periode yang memberikan peningkatan penjualan "
                "lebih besar, seperti Thanksgiving dan Desember, dapat "
                "menjadi prioritas dibandingkan promosi pada periode "
                "dengan peningkatan yang lebih rendah."
            ),
            bukti=(
                f"Dampak penjualan pada Super Bowl sebesar {pct(sb, 1)} "
                f"dan Labor Day sebesar {pct(lb, 1)} dibandingkan pekan biasa. "
                f"Angka tersebut lebih rendah dibandingkan peningkatan "
                f"penjualan pada Thanksgiving yang mencapai {pct(tg_lift, 0)}."
            ),
            aksi=[
                "Mengevaluasi kembali promosi berskala besar pada Super Bowl dan Labor Day.",
                "Menguji jenis promosi yang berbeda untuk mengetahui produk mana yang lebih diminati pelanggan pada periode tersebut.",
                "Mempertimbangkan pengalihan sebagian anggaran promosi ke periode dengan potensi peningkatan penjualan yang lebih tinggi."
            ],
            kpi=(
                "Hasil penjualan selama promosi dan perbandingan biaya promosi "
                "dengan peningkatan penjualan yang diperoleh."
            )
        ))

    # 10 — Faktor eksternal
    mx = drv["Korelasi dgn Indeks Toko"].abs().max()
    unemp = drv.loc[
        drv.Faktor == "Unemployment",
        "Korelasi dgn Indeks Toko"
    ].iloc[0]

    r2_store, r2_week = variance_explained(df)

    D.append(dict(
        prio="Rendah",
        area="Pemantauan Faktor Eksternal",
        keputusan=(
            "Faktor eksternal seperti suhu, harga bahan bakar, CPI, "
            "dan tingkat pengangguran tetap perlu diperhatikan, tetapi "
            "belum dapat dijadikan dasar utama dalam menentukan strategi "
            "penjualan berdasarkan hasil analisis saat ini."
        ),
        bukti=(
            f"Hasil analisis menunjukkan bahwa hubungan faktor eksternal "
            f"dengan indeks penjualan toko relatif lemah, dengan nilai "
            f"korelasi tertinggi secara absolut sebesar {mx:.2f}. "
            f"Korelasi tingkat pengangguran sendiri sebesar {unemp:.2f}. "
            f"Sebagai perbandingan, perbedaan karakteristik masing-masing "
            f"toko dapat menjelaskan {pct(r2_store, 0, False)} variasi "
            f"penjualan. Sementara itu, pola pekan dalam satu tahun "
            f"menjelaskan {pct(r2_week, 0, False)} variasi indeks penjualan "
            f"setelah perbedaan skala toko diperhitungkan."
        ),
        aksi=[
            "Analisis penjualan sebaiknya lebih memperhatikan karakteristik toko, pola musiman, dan periode hari libur.",
            "Perubahan tingkat pengangguran di suatu wilayah tetap dapat dipantau sebagai informasi tambahan.",
            "Melakukan analisis lebih lanjut berdasarkan wilayah sebelum menentukan apakah faktor eksternal perlu dimasukkan ke dalam strategi penjualan."
        ],
        kpi=(
            "Perbandingan akurasi perkiraan penjualan sebelum dan sesudah "
            "memasukkan faktor eksternal."
        )
    ))

    order = {"Tinggi": 0, "Menengah": 1, "Rendah": 2}
    return sorted(D, key=lambda d: order[d["prio"]])
