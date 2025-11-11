import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Proto-Harmonic Lexicon Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load Data ---
DATA_PATH = "data/motifs_expanded.csv"

@st.cache_data
def load_data():
    try:
        df = pd.read_csv(DATA_PATH)
        return df
    except Exception as e:
        st.error(f"Error loading dataset: {e}")
        return pd.DataFrame()

df = load_data()

# --- Build summary dataset for dashboard ---
if not df.empty:
    summary_df = (
        df.groupby("culture_region")
        .agg(
            mean_cross_entropy_score=("cross_entropy_score", "mean"),
            dominant_ratio=("harmonic_ratio", lambda x: x.mode()[0] if not x.mode().empty else None),
        )
        .reset_index()
    )
else:
    summary_df = pd.DataFrame(columns=["culture_region", "mean_cross_entropy_score", "dominant_ratio"])

# --- Sidebar Filters ---
st.sidebar.header("Filter Parameters")

if not df.empty:
    region_options = sorted(df["culture_region"].dropna().unique().tolist())
    ratio_options = sorted(df["harmonic_ratio"].dropna().unique().tolist())

    selected_regions = st.sidebar.multiselect("Regions", region_options, default=region_options)
    selected_ratios = st.sidebar.multiselect("Harmonic Ratios", ratio_options, default=ratio_options)

    filtered = df[
        (df["culture_region"].isin(selected_regions)) &
        (df["harmonic_ratio"].isin(selected_ratios))
    ]
else:
    filtered = pd.DataFrame()

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📜 Overview",
    "📈 Correlation Map",
    "🌀 Symbol Timeline",
    "📚 Lexicon Table",
    "🖼️ Symbol Gallery",
    "🔍 Motif Insights",
    "🧭 Harmonic Dashboard",
    "🔺 Triadic Symbol Viewer"
])

# --- Tab 1: Overview ---
with tab1:
    st.title("Proto-Harmonic Lexicon Explorer")
    st.markdown("""
    Explore the cross-cultural harmonic relationships between early **Mediterranean** and **Tamil** symbol sequences.
    Use the filters on the left to refine motifs by region and harmonic ratio.
    """)

# --- Tab 2: Correlation Map ---
with tab2:
    st.subheader("📈 Harmonic Correlation Map")
    if not filtered.empty and {"latitude", "longitude"}.issubset(filtered.columns):
        st.map(filtered, latitude="latitude", longitude="longitude", size=5, color="#ffaa00")
    else:
        st.info("No geospatial data available.")

# --- Tab 3: Symbol Timeline ---
with tab3:
    st.subheader("🌀 Harmonic Ratio Timeline")
    if not filtered.empty and "chronology_bce" in filtered.columns:
        def ratio_to_float(r):
            try:
                a, b = r.split(":")
                return float(a) / float(b)
            except Exception:
                return None

        filtered["ratio_value"] = filtered["harmonic_ratio"].apply(ratio_to_float)
        valid = filtered.dropna(subset=["ratio_value", "chronology_bce"])

        if not valid.empty:
            fig = px.scatter(
                valid,
                x="chronology_bce",
                y="ratio_value",
                color="culture_region",
                hover_name="symbol_name",
                size="cross_entropy_score",
                title="Chronological Distribution of Harmonic Ratios"
            )
            fig.update_xaxes(autorange="reversed", title="Chronology (BCE)")
            fig.update_yaxes(title="Harmonic Ratio Value")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No chronological or ratio data available for selected motifs.")
    else:
        st.info("Chronological data not found in dataset.")

# --- Tab 4: Lexicon Table ---
with tab4:
    st.subheader("📚 Lexicon Table View")
    if not filtered.empty:
        st.dataframe(filtered)
    else:
        st.warning("No motifs found for the selected filters.")

# --- Tab 5: Symbol Gallery ---
with tab5:
    st.subheader("🖼️ Symbol Motif Gallery")
    if "symbol_image_path" in filtered.columns:
        show_images = st.sidebar.checkbox("Show motif images", value=True)
        if show_images:
            valid_images = filtered["symbol_image_path"].dropna().unique().tolist()
            if len(valid_images) > 0:
                # Ensure correct pairing of images and captions
                gallery_df = filtered.dropna(subset=["symbol_image_path"])
                gallery_df = gallery_df[gallery_df["symbol_image_path"].isin(valid_images)]

                images = gallery_df["symbol_image_path"].tolist()
                captions = gallery_df["symbol_name"].tolist()

                st.image(images, caption=captions, width=250)
            else:
                st.info("No motif images available for current selection.")
        else:
            st.info("Motif image display disabled.")
    else:
        st.info("🖼️ No image path column found in dataset.")

# --- Tab 6: Motif Insights ---
with tab6:
    st.subheader("🔍 Detailed Motif Insights")
    if not filtered.empty:
        selected_symbol = st.selectbox("Choose a motif:", filtered["symbol_name"].unique())
        details = filtered[filtered["symbol_name"] == selected_symbol].iloc[0]
        st.markdown(f"### **{details['symbol_name']}** ({details['culture_region']})")
        st.markdown(f"- **Site:** {details['site_name']}")
        st.markdown(f"- **Harmonic Ratio:** {details['harmonic_ratio']}")
        st.markdown(f"- **Cross-Entropy Score:** {details['cross_entropy_score']}")
        st.markdown(f"- **Chronology (BCE):** {details['chronology_bce']}")
        st.markdown(f"- **Concept:** {details['probable_concept']}")
        st.markdown(f"- **Description:** {details['description']}")
    else:
        st.info("No motifs available for insight view.")

# --- Tab 7: Harmonic Dashboard ---
with tab7:
    st.subheader("🧭 Integrated Harmonic Dashboard")

    if not df.empty and not summary_df.empty:
        col1, col2 = st.columns((2, 2))

        # --- Map ---
        with col1:
            st.markdown("### 🌍 Cultural Distribution Map")
            if {"latitude", "longitude"}.issubset(df.columns):
                valid_geo = df.dropna(subset=["latitude", "longitude"])
                if not valid_geo.empty:
                    st.map(valid_geo, latitude="latitude", longitude="longitude", size=5, color="#ffaa00")
                else:
                    st.info("No geospatial data available.")
            else:
                st.info("Latitude/longitude columns missing.")

        # --- Summary Chart ---
        with col2:
            st.markdown("### 🔆 Mean Symbolic Intensity by Region")
            if "mean_cross_entropy_score" in summary_df.columns:
                fig_bar = px.bar(
                    summary_df,
                    x="culture_region",
                    y="mean_cross_entropy_score",
                    color="dominant_ratio",
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                    text="dominant_ratio",
                    title="Regional Harmonic Profile"
                )
                fig_bar.update_traces(textposition="outside")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Summary data not yet built.")

        # --- Timeline ---
        st.markdown("### ⏳ Frequency Evolution Overview")

        def ratio_to_float(r):
            try:
                a, b = r.split(":")
                return float(a) / float(b)
            except Exception:
                return None

        df["ratio_value"] = df["harmonic_ratio"].apply(ratio_to_float)
        valid = df.dropna(subset=["ratio_value", "chronology_bce"])

        if not valid.empty:
            fig_timeline = px.scatter(
                valid,
                x="chronology_bce",
                y="ratio_value",
                color="culture_region",
                size="cross_entropy_score",
                hover_name="symbol_name",
                color_discrete_sequence=px.colors.qualitative.Set2,
                title="Timeline of Harmonic Ratios (4000–700 BCE)"
            )
            fig_timeline.update_traces(mode="markers+lines")
            fig_timeline.update_xaxes(autorange="reversed", title="Chronology (BCE)")
            fig_timeline.update_yaxes(title="Harmonic Ratio Value")
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Not enough ratio data for timeline display.")

        st.caption("The dashboard unites spatial, temporal, and harmonic data to reveal shared geometric cognition across early civilizations.")
    else:
        st.warning("Dataset or summary data not loaded.")

# --- Tab 8: Triadic Viewer ---
tab8 = st.tabs(["🔺 Triadic Symbol Viewer"])[0]

with tab8:
    st.subheader("🔺 Triadic Symbol Viewer")
    st.markdown("""
    This panel displays the three core harmonic motifs forming the proto-symbolic triad:
    **Creation → Duality → Life-from-Water**.
    """)

    # Define motif metadata
    motifs = [
        {
            "name": "Spiral-Triskelion",
            "ratio": "3:2",
            "concept": "Cycle of Creation / Renewal",
            "path": "data/images/M0001.svg"
        },
        {
            "name": "Twin Serpents",
            "ratio": "5:3",
            "concept": "Energy Duality / Magnetic Balance",
            "path": "data/images/IMG0002.png"
        },
        {
            "name": "Water-Seed Glyph",
            "ratio": "2:1",
            "concept": "Life from the Hidden Waters",
            "path": "data/images/IMG0003.png"
        },
    ]

    # Display side-by-side
    col1, col2, col3 = st.columns(3)

    for col, motif in zip([col1, col2, col3], motifs):
        with col:
            if os.path.exists(motif["path"]):
                st.image(motif["path"], use_container_width=True)
            else:
                st.warning(f"Image not found: {motif['path']}")

            st.markdown(f"**{motif['name']}**")
            st.caption(f"Harmonic Ratio: {motif['ratio']}  \nConcept: {motif['concept']}")
            
