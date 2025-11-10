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

# ----------------------------------------------
# SIDEBAR FILTERS
# ----------------------------------------------
with st.sidebar:
    st.header("Filter Parameters")

    regions = st.multiselect(
        "Region",
        options=sorted(df['culture_region'].dropna().unique()),
        default=sorted(df['culture_region'].dropna().unique())
    )

    ratios = st.multiselect(
        "Harmonic Ratios",
        options=sorted(df['harmonic_ratio'].dropna().unique()),
        default=sorted(df['harmonic_ratio'].dropna().unique())
    )

    clusters = st.multiselect(
        "Frequency Cluster",
        options=sorted(df['frequency_cluster'].dropna().unique()),
        default=sorted(df['frequency_cluster'].dropna().unique())
    )

    min_score = st.slider("Min Cross-Entropy Score", 0.0, 1.0, 0.6, 0.01)
    show_images = st.checkbox("Show motif image", value=True)

    st.markdown("---")

    # Safe downloads
    if os.path.exists('data/motifs_expanded.csv'):
        st.download_button(
            "Download CSV",
            data=open('data/motifs_expanded.csv', 'rb').read(),
            file_name='motifs_expanded.csv',
            mime='text/csv'
        )
    if os.path.exists('data/motifs.json'):
        st.download_button(
            "Download JSON",
            data=open('data/motifs.json', 'rb').read(),
            file_name='motifs.json',
            mime='application/json'
        )

# ----------------------------------------------
# FILTER DATA
# ----------------------------------------------
filtered = df[
    (df['culture_region'].isin(regions)) &
    (df['harmonic_ratio'].isin(ratios)) &
    (df['frequency_cluster'].isin(clusters)) &
    (df['cross_entropy_score'] >= min_score)
]

st.sidebar.markdown(f"**Filtered motifs:** {len(filtered)}")

# ----------------------------------------------
# MAIN LAYOUT: TABS
# ----------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "Atlas View",
    "Resonance Wheel",
    "Motif Detail"
])

# ============================================================
# TAB 1: ATLAS VIEW (MAP + NETWORK)
# ============================================================
with tab1:
    st.subheader("Geographic Distribution")
    if filtered[['latitude', 'longitude']].dropna().shape[0] > 0:
        st.map(
            filtered[['latitude', 'longitude']]
            .rename(columns={'latitude': 'lat', 'longitude': 'lon'})
            .dropna()
        )
    else:
        st.info("No geographic coordinates available for selected motifs.")

    st.subheader("Spectral Distribution")
    if not filtered.empty:
        fig = px.scatter(
            filtered,
            x='node_density',
            y='cross_entropy_score',
            color='culture_region',
            hover_data=['id', 'symbol_name', 'harmonic_ratio']
        )
        fig.update_layout(height=350, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data to display for current filters.")

    st.subheader("Motif Correlation Network (strong matches)")
    G = nx.Graph()

    for _, row in filtered.iterrows():
        G.add_node(row['id'],
                   label=row['symbol_name'],
                   region=row['culture_region'],
                   ratio=row['harmonic_ratio'],
                   score=row['cross_entropy_score'])
        match = row.get('comparative_match', '')
        if isinstance(match, str) and match.strip() != '':
            if match in filtered['id'].values:
                w = (
                    float(row.get('cross_entropy_score', 0.0)) +
                    float(filtered[filtered['id'] == match].iloc[0]['cross_entropy_score'])
                ) / 2.0
                G.add_edge(row['id'], match, weight=w)

    if len(G.nodes) > 0:
        pos = nx.spring_layout(G, seed=42, k=0.5)
        edge_x, edge_y = [], []
        for u, v in G.edges():
            x0, y0 = pos[u]; x1, y1 = pos[v]
            edge_x += [x0, x1, None]; edge_y += [y0, y1, None]

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=1, color='#999'),
            hoverinfo='none'
        )

        node_x, node_y, node_text, node_color = [], [], [], []
        for n, data in G.nodes(data=True):
            x, y = pos[n]
            node_x.append(x); node_y.append(y)
            node_text.append(f"{n}: {data.get('label', '')}\n"
                             f"{data.get('region', '')} | ratio={data.get('ratio', '')} | score={data.get('score', '')}")
            node_color.append(0 if data.get('region') == 'Mediterranean' else 1)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            marker=dict(size=18, color=node_color, colorscale='Portland'),
            hovertext=node_text,
            hoverinfo='text'
        )

        fig2 = go.Figure(data=[edge_trace, node_trace],
                         layout=go.Layout(showlegend=False, height=450, margin=dict(t=20, b=20, l=20, r=20)))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No network edges found for current filter set.")

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
# TAB 3: MOTIF DETAIL VIEW
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
