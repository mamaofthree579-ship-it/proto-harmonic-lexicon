import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Proto-Harmonic Lexicon Explorer", layout="wide")

# --- Load data ---
@st.cache_data
def load_data():
    file_path = "data/motifs_expanded.csv"
    if not os.path.exists(file_path):
        st.error("❌ Could not find data/motifs_expanded.csv")
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    return df

df = load_data()

st.title("🌐 Proto-Harmonic Lexicon Explorer")
st.markdown("Explore symbolic harmonics between early Mediterranean and Tamil traditions.")

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filter Parameters")

region_filter = st.sidebar.multiselect(
    "Select Region(s):",
    options=sorted(df['culture_region'].dropna().unique()) if 'culture_region' in df else [],
    default=None
)

ratio_filter = st.sidebar.multiselect(
    "Select Harmonic Ratio(s):",
    options=sorted(df['harmonic_ratio'].dropna().unique()) if 'harmonic_ratio' in df else [],
    default=None
)

cluster_filter = st.sidebar.multiselect(
    "Select Frequency Cluster(s):",
    options=sorted(df['frequency_cluster'].dropna().unique()) if 'frequency_cluster' in df else [],
    default=None
)

# --- Apply Filters ---
filtered = df.copy()

if region_filter:
    filtered = filtered[filtered['culture_region'].isin(region_filter)]

if ratio_filter:
    filtered = filtered[filtered['harmonic_ratio'].isin(ratio_filter)]

if cluster_filter:
    filtered = filtered[filtered['frequency_cluster'].isin(cluster_filter)]

# --- Tabs Layout ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📜 Data Overview",
    "🗺️ Atlas Map",
    "🌀 Harmonic Wheel",
    "⏳ Chronological Timeline"
])

# --- Tab 1: Data Overview ---
with tab1:
    st.subheader("📖 Motif Dataset Overview")
    st.dataframe(filtered, use_container_width=True)

    st.download_button(
        "⬇️ Download Filtered Data as CSV",
        filtered.to_csv(index=False).encode('utf-8'),
        "filtered_motifs.csv",
        "text/csv"
    )

    # --- Motif Image Gallery ---
    if 'symbol_image_path' in filtered.columns:
        show_images = st.sidebar.checkbox("🖼️ Show motif images", value=True)
        if show_images:
            valid_images = filtered['symbol_image_path'].dropna().unique().tolist()
            if len(valid_images) > 0:
                st.subheader("🖼️ Symbol Motif Gallery")
                captions = filtered.set_index('symbol_image_path')['symbol_name'].to_dict()
                for img_path in valid_images:
                    if os.path.exists(img_path):
                        st.image(img_path, caption=captions.get(img_path, ""), width=250)
                    else:
                        st.warning(f"⚠️ Image not found: {img_path}")
            else:
                st.info("No motif images available for the current selection.")
    else:
        st.sidebar.info("🖼️ Image path column not found in dataset.")

# --- Tab 2: Atlas Map ---
with tab2:
    st.subheader("🗺️ Geo-Cultural Atlas")
    if 'latitude' in filtered.columns and 'longitude' in filtered.columns:
        valid_geo = filtered.dropna(subset=['latitude', 'longitude'])
        if not valid_geo.empty:
            st.map(valid_geo, latitude='latitude', longitude='longitude', size=5, color="#ffaa00")
            st.caption("Geographic distribution of motifs with harmonic resonance clusters.")
        else:
            st.warning("No valid geographic coordinates found in the filtered data.")
    else:
        st.error("Geolocation columns missing (latitude / longitude).")

# --- Tab 3: Harmonic Wheel ---
with tab3:
    st.subheader("🌀 Harmonic Resonance Wheel")

    if 'harmonic_ratio' in filtered.columns and not filtered.empty:
        fig = px.scatter_polar(
            filtered,
            r="cross_entropy_score",
            theta="harmonic_ratio",
            color="frequency_cluster",
            hover_name="symbol_name",
            size="cross_entropy_score",
            size_max=20,
            color_discrete_sequence=px.colors.sequential.Plasma
        )
        fig.update_layout(
            polar=dict(radialaxis=dict(showticklabels=False, ticks='')),
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Insufficient data to generate harmonic wheel.")

# --- Tab 4: Chronological Timeline ---
with tab4:
    st.subheader("⏳ Motif Chronology (BCE)")

    if 'chronology_bce' in filtered.columns and not filtered.empty:
        df_timeline = filtered.copy()

        # Extract numeric values from "3400 BCE" etc.
        df_timeline['chronology_bce_numeric'] = (
            df_timeline['chronology_bce']
            .astype(str)
            .str.extract(r'(\d+)')
            .astype(float)
        )
        df_timeline.dropna(subset=['chronology_bce_numeric'], inplace=True)

        if not df_timeline.empty:
            fig_time = px.scatter(
                df_timeline.sort_values('chronology_bce_numeric', ascending=False),
                x='chronology_bce_numeric',
                y='symbol_name',
                color='culture_region',
                size='cross_entropy_score',
                hover_data=['harmonic_ratio', 'probable_concept', 'site_name'],
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_time.update_layout(
                xaxis_title="Approximate Date (BCE → CE)",
                yaxis_title="Motif Name",
                xaxis_autorange="reversed",
                showlegend=True
            )
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.warning("No valid chronological data found.")
    else:
        st.error("Chronology column missing from dataset.")

# --- Footer ---
st.markdown("---")
st.caption("Developed as part of the Proto-Harmonic Lexicon Open Project © 2025.")
