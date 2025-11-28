import streamlit as st
from datetime import time
import osmnx as ox

st.set_page_config(page_title="Bologna Shadow Routing", layout="wide")
st.title("Bologna Shadow-aware Routing")

# ---- Bologna bounding box (your AOI) ----
north = 44.50776772181009
south = 44.49584275842293
west  = 11.32117165803459
east  = 11.346221029006651

st.sidebar.header("Route settings")

start_lat = st.sidebar.number_input("Start latitude", value=44.4985, format="%.6f")
start_lon = st.sidebar.number_input("Start longitude", value=11.3250, format="%.6f")

end_lat = st.sidebar.number_input("End latitude", value=44.5055, format="%.6f")
end_lon = st.sidebar.number_input("End longitude", value=11.3420, format="%.6f")

route_time = st.sidebar.slider(
    "Select time (27 July 2025)",
    min_value=time(10, 0),
    max_value=time(20, 0),
    value=time(15, 0),
    step=60
)

alpha = st.sidebar.slider(
    "Alpha (sun penalty)",
    min_value=0,
    max_value=500,
    value=50,
    step=10
)

compute = st.sidebar.button("Compute routes")

st.write("### Status")

if compute:
    st.write("✅ Loading road network from OpenStreetMap...")

    G = ox.graph_from_bbox(
        north, south, east, west, network_type="walk"
    )

    st.write(f"✅ Graph loaded with {len(G.nodes)} nodes and {len(G.edges)} edges")
else:
    st.info("Set parameters and click 'Compute routes'.")
