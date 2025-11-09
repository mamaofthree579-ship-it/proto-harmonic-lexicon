import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Proto-Harmonic Lexicon Atlas")

@st.cache_data
def load_data(path="data/motifs.csv"):
    return pd.read_csv(path)

df = load_data("data/motifs.csv")

st.title("Proto-Shared Harmonic Lexicon — Atlas (Streamlit Prototype)")
st.markdown("Interactive exploration of motif correlations between Mediterranean and Tamil/Indus traditions.")

# Sidebar filters
regions = st.sidebar.multiselect("Filter by region", options=sorted(df['culture_region'].unique()), default=sorted(df['culture_region'].unique()))
ratios = st.sidebar.multiselect("Harmonic ratio", options=sorted(df['harmonic_ratio'].unique()), default=sorted(df['harmonic_ratio'].unique()))
min_score = st.sidebar.slider("Minimum cross-entropy score", 0.0, 1.0, 0.6, 0.01)

filtered = df[(df['culture_region'].isin(regions)) & (df['harmonic_ratio'].isin(ratios)) & (df['cross_entropy_score']>=min_score)]

st.sidebar.markdown(f"Filtered motifs: **{len(filtered)}**")

# Show map of sites
st.subheader("Geographic distribution (filtered motifs)")
if 'latitude' in filtered.columns and 'longitude' in filtered.columns:
    st.map(filtered[['latitude','longitude']].dropna().rename(columns={'latitude':'lat','longitude':'lon'}))

# Network graph: build edges from comparative_match
st.subheader("Motif correlation network")
G = nx.Graph()
for _, row in filtered.iterrows():
    G.add_node(row['id'], label=row['symbol_name'], region=row['culture_region'], ratio=row['harmonic_ratio'], score=row['cross_entropy_score'])
    # add edge if comparative_match exists and present in filtered
    match = row.get('comparative_match', None)
    if isinstance(match, str) and match.strip() != "":
        if match in filtered['id'].values:
            # find matched row to get score
            matched_row = filtered[filtered['id']==match].iloc[0]
            w = float((row.get('cross_entropy_score',0.0) + matched_row.get('cross_entropy_score',0.0)) / 2.0)
            G.add_edge(row['id'], match, weight=w)

# plot using Plotly
pos = nx.spring_layout(G, seed=42)
edge_x = []
edge_y = []
edge_w = []
for u,v,data in G.edges(data=True):
    x0,y0 = pos[u]
    x1,y1 = pos[v]
    edge_x += [x0, x1, None]
    edge_y += [y0, y1, None]
    edge_w.append(data.get('weight', 0.5))

edge_trace = go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(width=1, color='#888'), hoverinfo='none')

node_x = []
node_y = []
node_text = []
for n,data in G.nodes(data=True):
    x,y = pos[n]
    node_x.append(x)
    node_y.append(y)
    node_text.append(f"{n}: {data.get('label','')}\n{data.get('region','')} | ratio={data.get('ratio','')}")

node_trace = go.Scatter(x=node_x, y=node_y, mode='markers+text', textposition="top center",
                        marker=dict(size=20, color=[1 if data.get('region')=='Mediterranean' else 2 for _,data in G.nodes(data=True)]),
                        text=[data.get('label','') for _,data in G.nodes(data=True)],
                        hovertext=node_text, hoverinfo='text')

fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(showlegend=False, hovermode='closest',
                                 margin=dict(b=20,l=5,r=5,t=40)))
st.plotly_chart(fig, use_container_width=True)

# Detailed table & export
st.subheader("Filtered motif table")
st.dataframe(filtered)

csv = filtered.to_csv(index=False).encode('utf-8')
st.download_button("Download filtered CSV", data=csv, file_name="filtered_motifs.csv", mime="text/csv")

st.markdown("---")
st.markdown("## About\nThis is a prototype Streamlit app to explore the proto-shared harmonic lexicon dataset. Adapt and extend as needed.")
