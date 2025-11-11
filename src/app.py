import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import math
import os

st.set_page_config(page_title="Proto-Harmonic Lexicon Explorer", layout="wide")

# --- Load Data ---
@st.cache_data
def load_data():
    file_path = "data/motifs_expanded.csv"
    if not os.path.exists(file_path):
        st.error("❌ Could not find data/motifs_expanded.csv")
        return pd.DataFrame()
    df = pd.read_csv(file_path)
    return df

df = load_data()
def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-region harmonic summaries."""
    if df.empty:
        return pd.DataFrame()

    # Convert ratios such as '5:3' safely
    def safe_ratio(val):
        return val if isinstance(val, str) and ':' in val else None
    df = df.copy()
    df['harmonic_ratio'] = df['harmonic_ratio'].apply(safe_ratio)

    summary = (
        df.groupby('culture_region')
          .apply(lambda g: pd.Series({
              "count": len(g),
              "dominant_ratio": g['harmonic_ratio'].mode().iloc[0] if not g['harmonic_ratio'].mode().empty else None,
              "mean_cross_entropy_score": round(g['cross_entropy_score'].mean(), 3),
              "mean_chronology_bce": round(g['chronology_bce'].mean(), 0)
          }))
          .reset_index()
    )
    summary.to_csv("data/harmonic_summary.csv", index=False)
    return summary
    
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, = st.tabs([
    "📜 Data Overview",
    "🗺️ Atlas Map",
    "🌀 Harmonic Wheel",
    "⏳ Chronological Timeline",
    "🎶 Frequency Geometry Visualizer"
    "📊 Harmonic Correlation Table"
    "🧭 Harmonic Dashboard"
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

# --- Tab 5: Frequency Geometry Visualizer ---
with tab5:
    st.subheader("🎶 Frequency Geometry Visualizer")

    if 'harmonic_ratio' in filtered.columns and not filtered.empty:
        selected_ratios = filtered['harmonic_ratio'].dropna().unique().tolist()

        if selected_ratios:
            ratio_choice = st.selectbox("Select a harmonic ratio to visualize:", selected_ratios)
            
            # Parse ratio
            try:
                num, den = map(float, ratio_choice.split(":"))
                ratio_value = num / den
            except:
                st.error("Invalid ratio format.")
                ratio_value = 1.0

            # Generate chord geometry
            steps = 24
            angles = [i * 2 * math.pi / steps for i in range(steps)]
            x_points = [math.cos(a) for a in angles]
            y_points = [math.sin(a) for a in angles]

            fig_geo = go.Figure()
            fig_geo.add_trace(go.Scatter(
                x=x_points + [x_points[0]],
                y=y_points + [y_points[0]],
                mode="lines",
                line=dict(color="lightgray", width=1),
                name="Circle"
            ))

            # Add ratio chords
            chord_count = int(num + den)
            for i in range(chord_count):
                start_angle = (2 * math.pi / chord_count) * i
                end_angle = start_angle * ratio_value
                x0, y0 = math.cos(start_angle), math.sin(start_angle)
                x1, y1 = math.cos(end_angle), math.sin(end_angle)
                fig_geo.add_trace(go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode="lines",
                    line=dict(width=2, color="gold"),
                    showlegend=False
                ))

            fig_geo.update_layout(
                title=f"Harmonic Geometry for Ratio {ratio_choice}  →  {round(ratio_value, 3)}",
                xaxis=dict(showticklabels=False, visible=False),
                yaxis=dict(showticklabels=False, visible=False),
                width=600,
                height=600,
                plot_bgcolor="black",
                paper_bgcolor="black"
            )

            st.plotly_chart(fig_geo, use_container_width=True)
        else:
            st.info("No harmonic ratios available in dataset.")
    else:
        st.warning("Harmonic ratio column missing or empty.")

# --- Tab 5: Frequency Evolution ---
tab5 = st.tabs(["🎼 Frequency Evolution"])[0]

with tab5:
    st.subheader("🎼 Harmonic Frequency Evolution Across Time")

    if not df.empty and 'harmonic_ratio' in df.columns and 'chronology_bce' in df.columns:
        # Convert harmonic_ratio like '5:3' to numeric float
        def ratio_to_float(r):
            try:
                a, b = r.split(':')
                return float(a) / float(b)
            except Exception:
                return None

        df['ratio_value'] = df['harmonic_ratio'].apply(ratio_to_float)
        valid = df.dropna(subset=['ratio_value', 'chronology_bce'])

        # --- Scatter Line Plot (Frequency Evolution) ---
        fig_timeline = px.scatter(
            valid,
            x='chronology_bce',
            y='ratio_value',
            color='culture_region',
            size='cross_entropy_score',
            hover_name='symbol_name',
            color_discrete_sequence=px.colors.qualitative.Set2,
            labels={
                "chronology_bce": "Chronology (BCE)",
                "ratio_value": "Harmonic Ratio (Numeric)"
            },
            title="Frequency Evolution by Civilization"
        )
        fig_timeline.update_traces(mode="markers+lines")
        fig_timeline.update_xaxes(autorange="reversed")  # BCE timeline descending
        st.plotly_chart(fig_timeline, use_container_width=True)

        # --- Ratio Density Heatmap ---
        density = valid.groupby(['culture_region', 'harmonic_ratio']).size().reset_index(name='count')
        fig_heat = px.density_heatmap(
            density,
            x='harmonic_ratio',
            y='culture_region',
            z='count',
            color_continuous_scale='Viridis',
            title="Harmonic Ratio Density by Region"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.caption("Ratios trend toward convergence around 3:2 and 5:3 across eras, suggesting cognitive harmonic continuity.")
    else:
        st.warning("Frequency or chronological data missing — unable to plot frequency evolution.")
# --- Tab 6: Harmonic Correlation Table ---
tab6 = st.tabs(["📊 Harmonic Correlation Table"])[0]

with tab6:
    st.subheader("📊 Comparative Harmonic Summary by Region")

    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True)

        fig_summary = px.bar(
            summary_df,
            x="culture_region",
            y="mean_cross_entropy_score",
            color="dominant_ratio",
            text="mean_cross_entropy_score",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Average Symbolic Intensity per Culture"
        )
        fig_summary.update_traces(textposition="outside")
        st.plotly_chart(fig_summary, use_container_width=True)

        st.caption("Regions cluster near similar harmonic intensities, reinforcing cross-cultural resonance patterns.")
    else:
        st.warning("Summary data not available. Ensure motifs_expanded.csv is loaded correctly.")
 # --- Tab 7: Harmonic Dashboard ---
tab7 = st.tabs(["🧭 Harmonic Dashboard"])[0]

with tab7:
    st.subheader("🧭 Integrated Harmonic Dashboard")

    if not df.empty:
        col1, col2 = st.columns((2, 2))
        # ----- Map -----
        with col1:
            st.markdown("### 🌍 Cultural Distribution Map")
            if 'latitude' in df.columns and 'longitude' in df.columns:
                valid_geo = df.dropna(subset=['latitude', 'longitude'])
                if not valid_geo.empty:
                    st.map(valid_geo, latitude='latitude', longitude='longitude', size=5, color="#ffaa00")
                else:
                    st.info("No geospatial data available.")
            else:
                st.info("Latitude/longitude columns missing.")

        # ----- Summary Bar -----
        with col2:
            st.markdown("### 🔆 Mean Symbolic Intensity by Region")
            if 'mean_cross_entropy_score' in summary_df.columns:
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

        # ----- Timeline / Evolution -----
        st.markdown("### ⏳ Frequency Evolution Overview")

        def ratio_to_float(r):
            try:
                a, b = r.split(':')
                return float(a) / float(b)
            except Exception:
                return None

        df['ratio_value'] = df['harmonic_ratio'].apply(ratio_to_float)
        valid = df.dropna(subset=['ratio_value', 'chronology_bce'])
        if not valid.empty:
            fig_timeline = px.scatter(
                valid,
                x='chronology_bce',
                y='ratio_value',
                color='culture_region',
                size='cross_entropy_score',
                hover_name='symbol_name',
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
        st.warning("Dataset not loaded.")
        
# --- Footer ---
st.markdown("---")
st.caption("Developed as part of the Proto-Harmonic Lexicon Open Project © 2025.")
