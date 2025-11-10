import streamlit as st
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import json, os, base64, math

# ----------------------------------------------
# PAGE CONFIG
# ----------------------------------------------
st.set_page_config(
    layout='wide',
    page_title='Proto-Harmonic Lexicon Atlas',
    initial_sidebar_state='expanded'
)

# ----------------------------------------------
# LOAD DATA WITH SAFE FALLBACK
# ----------------------------------------------
@st.cache_data
def load_data(csv_path='data/motifs_expanded.csv', json_path='data/motifs.json'):
    """Load CSV and JSON data, create JSON if missing."""
    df = pd.read_csv(csv_path)
    j = None
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                j = json.load(f)
        except Exception:
            j = None
    else:
        # Auto-generate JSON if missing
        j = df.to_dict(orient='records')
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(j, f, ensure_ascii=False, indent=2)
    return df, j

df, jdata = load_data()

# =============================================
# FILTER PARAMETERS
# =============================================
st.sidebar.header("Filter Parameters")

# --- 1️⃣ Region filter ---
regions = sorted(df['culture_region'].dropna().unique()) if 'culture_region' in df.columns else []
region_selected = st.sidebar.multiselect("Select Region(s):", regions, default=regions)

# --- 2️⃣ Harmonic Ratios filter ---
ratios = sorted(df['harmonic_ratio'].dropna().unique()) if 'harmonic_ratio' in df.columns else []
ratio_selected = st.sidebar.multiselect("Select Harmonic Ratio(s):", ratios, default=ratios)

# --- 3️⃣ Frequency Cluster filter (safe auto-detect) ---
if 'frequency_cluster' in df.columns:
    freq_options = sorted(df['frequency_cluster'].dropna().unique())
    frequency_selected = st.sidebar.multiselect("Frequency Cluster(s):", freq_options, default=freq_options)
else:
    frequency_selected = []  # fallback so downstream filters won't break
    st.sidebar.info("⚙️ No 'frequency_cluster' column found — skipping this filter.")

# --- 4️⃣ Apply filters safely ---
filtered = df.copy()

if region_selected:
    filtered = filtered[filtered['culture_region'].isin(region_selected)]
if ratio_selected:
    filtered = filtered[filtered['harmonic_ratio'].isin(ratio_selected)]
if frequency_selected:
    filtered = filtered[filtered['frequency_cluster'].isin(frequency_selected)]

# ----------------------------------------------
# MAIN LAYOUT: TABS
# ----------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Atlas View",
    "Resonance Wheel",
    "Resonance Timeline",
    "Motif Detail"
])

# ============================================================
# TAB 1: ATLAS MAP VIEW — SAFE COORDINATE HANDLING
# ============================================================

with tab1:
    st.subheader("Cultural Motif Atlas — Mediterranean ↔ Tamil Continuum")

    # Check if coordinates exist
    if 'latitude' in filtered.columns and 'longitude' in filtered.columns:
        coords = filtered[['latitude', 'longitude']].dropna()
        if coords.shape[0] > 0:
            st.map(filtered, latitude='latitude', longitude='longitude')
        else:
            st.info("🗺️ No coordinate data available to map.")
    else:
        st.info("🗺️ Columns 'latitude' and 'longitude' not found — skipping map view.")

    st.markdown("""
    The Atlas visualizes the spatial distribution of motifs.  
    If latitude/longitude are not yet recorded, data can still be browsed and correlated via other tabs.
    """)

# ============================================================
# TAB 2: RESONANCE WHEEL (v3 — safe export + label control)
# ============================================================
with tab2:
    st.subheader("Resonance Wheel — Harmonic Frequency Map")

    if not filtered.empty:
        # Convert harmonic ratio to numeric angle
        def ratio_to_angle(r):
            try:
                a, b = map(float, str(r).split(':'))
                return (a / b) * 360 % 360
            except:
                return 0

        filtered['angle'] = filtered['harmonic_ratio'].apply(ratio_to_angle)
        filtered['radius'] = filtered['cross_entropy_score'] * 2 + 1

        # UI controls
        show_labels = st.checkbox("Show motif labels", value=False)
        point_size = st.slider("Point size", 5, 25, 12)
        opacity = st.slider("Point opacity", 0.3, 1.0, 0.8)

        fig3 = go.Figure()

        for region in filtered['culture_region'].unique():
            sub = filtered[filtered['culture_region'] == region]
            fig3.add_trace(go.Scatterpolar(
                r=sub['radius'],
                theta=sub['angle'],
                mode='markers+text' if show_labels else 'markers',
                text=sub['symbol_name'] if show_labels else None,
                textposition='top center',
                name=region,
                marker=dict(size=point_size, opacity=opacity, symbol='circle')
            ))

        fig3.update_layout(
            polar=dict(
                radialaxis=dict(visible=False),
                angularaxis=dict(direction='clockwise')
            ),
            showlegend=True,
            template="plotly_white",
            height=600,
            margin=dict(t=30, b=30, l=10, r=10)
        )

        st.plotly_chart(fig3, use_container_width=True)

        # --------------------------------------------------------
        # EXPORT SECTION (Safe)
        # --------------------------------------------------------
        st.markdown("#### Export Resonance Wheel")

        try:
            import kaleido  # ensure available
            from io import BytesIO

            buf_svg, buf_png = BytesIO(), BytesIO()
            fig3.write_image(buf_svg, format="svg")
            fig3.write_image(buf_png, format="png")
            st.download_button("Download as SVG",
                               data=buf_svg.getvalue(),
                               file_name="resonance_wheel.svg",
                               mime="image/svg+xml")
            st.download_button("Download as PNG",
                               data=buf_png.getvalue(),
                               file_name="resonance_wheel.png",
                               mime="image/png")
        except Exception as e:
            st.info(f"Export unavailable: {e}")
            st.caption("Install `pip install -U kaleido` locally for SVG/PNG export support.")

        st.caption("Tip: Hide labels for dense selections to avoid overlap.")
    else:
        st.warning("No motifs to visualize. Adjust filters.")


        st.caption("Tip: Hide labels for dense selections to avoid overlap.")
    
# ============================================================
# TAB 3: RESONANCE SPECTRUM TIMELINE (auto-detects chronology)
# ============================================================
with tab3:
    st.subheader("Resonance Spectrum Timeline — Harmonic Evolution")

    # --- 1️⃣ Detect available chronology column ---
    date_columns = [c for c in df.columns if any(k in c.lower() for k in ['chronology', 'date', 'year'])]
    if not date_columns:
        st.warning("No chronological or date-like column found. Please include a column such as 'chronology_bce' or 'date_estimated'.")
    else:
        chosen_col = date_columns[0]
        st.caption(f"Using detected column for chronology: `{chosen_col}`")

        if filtered.empty:
            st.warning("No motifs available for visualization.")
        else:
            st.markdown("""
            This timeline visualizes **when** each harmonic ratio appears in the archaeological
            or symbolic record, across regions.  
            Each point = one motif’s resonance frequency through time.
            """)

            # --- 2️⃣ Parse and normalize date values ---
            def parse_to_year(value):
                if value is None:
                    return None
                s = str(value).strip()
                if s == "" or s.lower() in ("nan", "none"):
                    return None
                s = s.replace("ca.", "").replace("c.", "").replace("approx", "").replace(",", "").strip()

                # handle ranges (e.g. "3400-3200 BCE")
                import re
                m = re.match(r'^(\d{3,4})\s*-\s*(\d{3,4})\s*(bce|ce)?', s, flags=re.I)
                if m:
                    num = int(m.group(1))
                    return -num if (m.group(3) and m.group(3).lower() == "bce") else num

                # BCE / CE
                m = re.search(r'(\d{2,4})\s*(bce|ce)', s, flags=re.I)
                if m:
                    num = int(m.group(1))
                    return -num if m.group(2).lower() == "bce" else num

                # negative numbers as BCE
                m = re.match(r'^-(\d{3,4})$', s)
                if m:
                    return -int(m.group(1))

                # plain numbers (heuristic)
                m = re.match(r'^(\d{2,4})$', s)
                if m:
                    num = int(m.group(1))
                    return -num if num >= 1000 else num

                # fallback: find first number
                m = re.search(r'(\d{2,4})', s)
                if m:
                    num = int(m.group(1))
                    return -num if num >= 1000 else num
                return None

            filtered['year'] = filtered[chosen_col].apply(parse_to_year)
            filtered = filtered.dropna(subset=['year'])

            if filtered.empty:
                st.info("No valid chronological values after parsing.")
            else:
                fig4 = px.scatter(
                    filtered.sort_values(by='year'),
                    x='year',
                    y='harmonic_ratio',
                    color='culture_region',
                    size='cross_entropy_score',
                    hover_data=['id', 'symbol_name', 'site_name', 'cross_entropy_score', chosen_col],
                    title="Temporal Distribution of Harmonic Ratios"
                )

                fig4.update_layout(
                    xaxis_title="Chronology (BCE → CE)",
                    yaxis_title="Harmonic Ratio",
                    height=500,
                    template="plotly_white",
                    margin=dict(t=40, b=20, l=20, r=20)
                )

                # invert x-axis so older BCE dates appear on the left
                fig4.update_xaxes(autorange="reversed")

                # --- 3️⃣ Optional smoothing trend line ---
                show_trend = st.checkbox("Show harmonic trend line", value=True)
                if show_trend:
                    trend = (
                        filtered.groupby('year')['cross_entropy_score']
                        .mean()
                        .reset_index()
                        .sort_values(by='year')
                    )
                    fig4.add_trace(go.Scatter(
                        x=trend['year'],
                        y=[t for t in trend['cross_entropy_score']],
                        mode='lines',
                        name='Avg Cross-Entropy Trend',
                        line=dict(color='black', dash='dot')
                    ))

                st.plotly_chart(fig4, use_container_width=True)

                st.caption("""
                • Older (BCE) motifs appear on the left; more recent (CE) motifs on the right.  
                • Larger dots = stronger symbolic correlation.  
                • Overlaps between regions suggest diffusion or parallel evolution.
                """)

# ============================================================
# TAB 4: MOTIF DETAIL VIEW
# ============================================================
with tab3:
    st.subheader("Motif Detail Viewer")

    if len(filtered) > 0:
        sel = st.selectbox(
            "Select motif ID",
            options=filtered['id'].tolist(),
            format_func=lambda x: f"{x} - {filtered[filtered['id'] == x]['symbol_name'].values[0]}"
        )

        row = filtered[filtered['id'] == sel].iloc[0]
        st.markdown(
            f"**{row['symbol_name']}**  \n"
            f"Region: {row['culture_region']}  \n"
            f"Site: {row['site_name']}  \n"
            f"Harmonic Ratio: {row['harmonic_ratio']}  \n"
            f"Cross-Entropy Score: {row['cross_entropy_score']}"
        )

        if show_images:
            img_path = os.path.join('data', 'images', os.path.basename(str(row.get('image_path', ''))))
            if os.path.exists(img_path):
                try:
                    svg = open(img_path, 'r', encoding='utf-8').read()
                    b64 = base64.b64encode(svg.encode('utf-8')).decode('utf-8')
                    html = f'<img src="data:image/svg+xml;base64,{b64}" ' \
                           f'style="width:100%;height:auto;border:1px solid #ccc;padding:6px;background:#fff"/>'
                    st.markdown(html, unsafe_allow_html=True)
                except Exception as e:
                    st.warning(f"Unable to render SVG for {img_path}: {e}")
            else:
                st.info("No image available for this motif.")
    else:
        st.warning("No motifs match the selected filters.")
        
st.markdown("---")
st.caption("© 2025 Proto-Harmonic Lexicon Project — MIT License (software), CC-BY-4.0 (data).")
