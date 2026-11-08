
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Walmart Retail BI",
    page_icon="📊",
    layout="wide"
)

# ==========================================
# 2. LOAD DATA
# ==========================================

@st.cache_data
def load_data():
    df = pd.read_csv("Walmart_Cleaned.csv")

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    df = df.dropna(
        subset=["Date", "Weekly_Sales", "Store"]
    )

    return df

df = load_data()

# ==========================================
# 3. SIDEBAR FILTER
# ==========================================

st.sidebar.title("📊 Walmart Retail BI")
st.sidebar.caption("Business Intelligence Dashboard")

st.sidebar.divider()

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

all_stores = sorted(df["Store"].unique())

selected_stores = st.sidebar.multiselect(
    "Select Store",
    all_stores,
    default=all_stores
)

if len(date_range) == 2:
    start_date, end_date = date_range

    data = df[
        (df["Date"].dt.date >= start_date) &
        (df["Date"].dt.date <= end_date) &
        (df["Store"].isin(selected_stores))
    ].copy()
else:
    data = df[
        df["Store"].isin(selected_stores)
    ].copy()

if data.empty:
    st.warning("No data available. Please change the filters.")
    st.stop()

# ==========================================
# 4. DASHBOARD HEADER
# ==========================================

st.title("Walmart Retail Business Intelligence")
st.write(
    "Sales Performance Analysis and Decision Support System"
)

st.caption(
    f"Data period: {data['Date'].min().date()} "
    f"to {data['Date'].max().date()}"
)

# ==========================================
# 5. NAVIGATION
# ==========================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview",
    "Store Performance",
    "Sales Trend",
    "Economic Analysis",
    "Decision Making"
])

# ==========================================
# TAB 1: OVERVIEW
# ==========================================

with tab1:

    st.subheader("Sales Overview")

    total_sales = data["Weekly_Sales"].sum()
    avg_sales = data["Weekly_Sales"].mean()
    highest_sales = data["Weekly_Sales"].max()
    total_stores = data["Store"].nunique()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Sales",
        f"${total_sales:,.0f}"
    )

    c2.metric(
        "Average Weekly Sales",
        f"${avg_sales:,.0f}"
    )

    c3.metric(
        "Highest Weekly Sales",
        f"${highest_sales:,.0f}"
    )

    c4.metric(
        "Total Stores",
        total_stores
    )

    st.divider()

    st.subheader("Monthly Sales Trend")

    monthly = (
        data.groupby(
            data["Date"].dt.to_period("M")
        )["Weekly_Sales"]
        .sum()
        .reset_index()
    )

    monthly["Date"] = monthly["Date"].astype(str)

    fig = px.line(
        monthly,
        x="Date",
        y="Weekly_Sales",
        markers=True,
        title="Monthly Total Sales"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ==========================================
# TAB 2: STORE PERFORMANCE
# ==========================================

with tab2:

    st.subheader("Store Performance Analysis")

    store_sales = (
        data.groupby("Store")["Weekly_Sales"]
        .agg(["sum", "mean"])
        .reset_index()
    )

    store_sales.columns = [
        "Store",
        "Total Sales",
        "Average Weekly Sales"
    ]

    store_sales = store_sales.sort_values(
        "Total Sales",
        ascending=False
    )

    fig = px.bar(
        store_sales,
        x="Store",
        y="Total Sales",
        color="Total Sales",
        title="Total Sales by Store",
        color_continuous_scale="Blues"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Store Ranking")

    st.dataframe(
        store_sales,
        use_container_width=True,
        hide_index=True
    )

# ==========================================
# TAB 3: SALES TREND
# ==========================================

with tab3:

    st.subheader("Sales Trend Analysis")

    weekly = (
        data.groupby("Date")["Weekly_Sales"]
        .sum()
        .reset_index()
    )

    fig = px.line(
        weekly,
        x="Date",
        y="Weekly_Sales",
        title="Weekly Sales Trend",
        markers=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader("Holiday Analysis")

    holiday = (
        data.groupby("Holiday_Flag")["Weekly_Sales"]
        .mean()
        .reset_index()
    )

    holiday["Period"] = holiday["Holiday_Flag"].map({
        0: "Non-Holiday",
        1: "Holiday"
    })

    fig2 = px.bar(
        holiday,
        x="Period",
        y="Weekly_Sales",
        color="Period",
        title="Average Sales: Holiday vs Non-Holiday"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    if len(holiday) == 2:
        normal = holiday.loc[
            holiday["Holiday_Flag"] == 0,
            "Weekly_Sales"
        ].iloc[0]

        holiday_avg = holiday.loc[
            holiday["Holiday_Flag"] == 1,
            "Weekly_Sales"
        ].iloc[0]

        difference = (
            (holiday_avg - normal) / normal
        ) * 100

        st.metric(
            "Holiday Sales Difference",
            f"{difference:.2f}%"
        )

# ==========================================
# TAB 4: ECONOMIC ANALYSIS
# ==========================================

with tab4:

    st.subheader("Economic Factors Analysis")

    economic_columns = [
        "Weekly_Sales",
        "Temperature",
        "Fuel_Price",
        "CPI",
        "Unemployment"
    ]

    corr = data[economic_columns].corr()

    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        title="Correlation Heatmap"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.info(
        "Correlation menunjukkan hubungan antarvariabel, "
        "bukan bukti hubungan sebab-akibat."
    )

# ==========================================
# TAB 5: DECISION MAKING
# ==========================================

with tab5:

    st.header("Business Decision Making")

    st.write(
        "Analisis ini membantu manajemen mengevaluasi "
        "performa toko dan menentukan target penjualan."
    )

    # Store evaluation

    st.subheader("1. Store Performance Evaluation")

    store_avg = (
        data.groupby("Store")["Weekly_Sales"]
        .mean()
        .reset_index()
    )

    overall_avg = data["Weekly_Sales"].mean()

    store_avg["Status"] = np.where(
        store_avg["Weekly_Sales"] >= overall_avg,
        "Above Average",
        "Below Average"
    )

    below_avg = store_avg[
        store_avg["Status"] == "Below Average"
    ]

    above_avg = store_avg[
        store_avg["Status"] == "Above Average"
    ]

    c1, c2 = st.columns(2)

    c1.metric(
        "Stores Above Average",
        len(above_avg)
    )

    c2.metric(
        "Stores Below Average",
        len(below_avg)
    )

    fig = px.bar(
        store_avg,
        x="Store",
        y="Weekly_Sales",
        color="Status",
        title="Average Weekly Sales by Store"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.markdown("### Business Recommendation")

    if len(below_avg) > 0:

        st.warning(
            f"{len(below_avg)} toko memiliki rata-rata "
            "penjualan di bawah rata-rata keseluruhan."
        )

        st.write(
            "Toko yang perlu dievaluasi:",
            below_avg["Store"].tolist()
        )

        st.write(
            "**Keputusan:** Manajemen dapat melakukan "
            "evaluasi terhadap strategi operasional dan "
            "kondisi pasar pada toko-toko tersebut."
        )

    else:

        st.success(
            "Semua toko berada di atas atau sama dengan "
            "rata-rata penjualan keseluruhan."
        )

    st.divider()

    # Sales target simulation

    st.subheader("2. Sales Target Simulation")

    growth_target = st.slider(
        "Target Sales Growth (%)",
        min_value=1,
        max_value=20,
        value=5
    )

    store_avg["Target Sales"] = (
        store_avg["Weekly_Sales"] *
        (1 + growth_target / 100)
    )

    store_avg["Target Difference"] = (
        store_avg["Target Sales"] -
        store_avg["Weekly_Sales"]
    )

    st.write(
        f"Target pertumbuhan yang dipilih: "
        f"{growth_target}%"
    )

    st.dataframe(
        store_avg,
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "Simulasi ini menggunakan asumsi target kenaikan "
        "penjualan yang sama untuk setiap toko. "
        "Nilainya bukan prediksi penjualan aktual."
    )

    st.divider()

    # Holiday strategy

    st.subheader("3. Holiday Business Strategy")

    holiday_result = (
        data.groupby("Holiday_Flag")["Weekly_Sales"]
        .mean()
    )

    if 0 in holiday_result.index and 1 in holiday_result.index:

        normal = holiday_result.loc[0]
        holiday_avg = holiday_result.loc[1]

        holiday_growth = (
            (holiday_avg - normal) / normal
        ) * 100

        st.metric(
            "Holiday Sales Difference",
            f"{holiday_growth:.2f}%"
        )

        if holiday_growth > 0:

            st.success(
                "Penjualan rata-rata pada minggu liburan "
                "lebih tinggi dibandingkan minggu biasa. "
                "Manajemen dapat mempertimbangkan persiapan "
                "operasional menjelang periode liburan."
            )

        else:

            st.warning(
                "Penjualan rata-rata pada minggu liburan "
                "tidak lebih tinggi. Manajemen perlu "
                "mengevaluasi strategi penjualan saat liburan."
            )

    else:

        st.info(
            "Data holiday dan non-holiday belum lengkap "
            "untuk perbandingan."
        )

    st.divider()

    # Download filtered dataset

    st.subheader("Download Analysis Data")

    st.download_button(
        "Download Filtered CSV",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="Walmart_Filtered.csv",
        mime="text/csv"
    )

# ==========================================
# FOOTER
# ==========================================

st.sidebar.divider()

st.sidebar.caption(
    "Walmart Retail BI Project | Business Intelligence"
)
