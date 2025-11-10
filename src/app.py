import streamlit as st
import pandas as pd
import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import json, os, base64

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
# TITLE AND DESCRIPTION
# ----------------------------------------------
st.title("Proto-Shared Harmonic Lexicon — Atlas")
st.caption("A cross-cultural dataset of symbolic harmonics across Mediterranean and Tamil/Indus civilizations")

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
# MAIN LAYOUT
# ----------------------------------------------
left, right = st.columns([2, 1])

# ==============================================
# LEFT PANEL — MAP + SPECTRAL DISTRIBUTION + NETWORK
# ==============================================
with left:
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
        fig.update_layout(
            height=350,
            margin=dict(t=30, b=10, l=10, r=10)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data to display for current filters.")

    st.subheader("Motif Correlation Network (strong matches)")
    G = nx.Graph()

    for _, row in filtered.iterrows():
        G.add_node(
            row['id'],
            label=row['symbol_name'],
            region=row['culture_region'],
            ratio=row['harmonic_ratio'],
            score=row['cross_entropy_score']
        )
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
            node_x.append(x)
            node_y.append(y)
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

        fig2 = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                showlegend=False,
                height=450,
                margin=dict(t=20, b=20, l=20, r=20)
            )
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No network edges found for current filter set.")

# ==============================================
# RIGHT PANEL — DETAIL VIEW
# ==============================================
with right:
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
