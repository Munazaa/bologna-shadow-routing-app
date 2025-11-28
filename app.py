import streamlit as st
from datetime import time, timedelta
import osmnx as ox
import networkx as nx
import leafmap.foliumap as leafmap

st.set_page_config(page_title="Bologna Shadow Routing", layout="wide")
st.title("Bologna Shadow-aware Routing")

# ---- Your AOI bounding box ----
north = 44.50776772181009
south = 44.49584275842293
west  = 11.32117165803459
east  = 11.346221029006651

# ---- Cache the OSM graph (FAST) ----
@st.cache_resource
def load_graph():
    return ox.graph_from_bbox(
        bbox=(north, south, east, west),
        network_type="walk"
    )

G = load_graph()

# ---- Session state ----
if "start_point" not in st.session_state:
    st.session_state.start_point = None

if "end_point" not in st.session_state:
    st.session_state.end_point = None

# ---- Sidebar ----
st.sidebar.header("Route settings")

route_time = st.sidebar.slider(
    "Select time (27 July 2025)",
    min_value=time(10, 0),
    max_value=time(20, 0),
    value=time(15, 0),
    step=timedelta(minutes=60)
)

alpha = st.sidebar.slider(
    "Alpha (sun penalty)",
    min_value=0,
    max_value=500,
    value=50,
    step=10
)

compute = st.sidebar.button("Compute routes")

# ---- Main Map (clickable) ----
st.write("### Click on the map to select points")

m = leafmap.Map(center=[44.5015, 11.334], zoom=15)
m.add_basemap("OpenStreetMap")

clicked = m.to_streamlit(height=600)

# ---- Store clicked coordinates safely ----
if clicked and len(clicked) > 0:
    last = clicked[-1]
    st.session_state.last_clicked = (last[1], last[0])  # (lat, lon)

# ---- Buttons to assign points ----
col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Set Start Point"):
        if "last_clicked" in st.session_state:
            st.session_state.start_point = st.session_state.last_clicked

with col2:
    if st.button("✅ Set End Point"):
        if "last_clicked" in st.session_state:
            st.session_state.end_point = st.session_state.last_clicked

# ---- Display chosen points ----
if st.session_state.start_point:
    st.sidebar.success(f"🟢 Start: {st.session_state.start_point}")

if st.session_state.end_point:
    st.sidebar.info(f"🔵 End: {st.session_state.end_point}")

# ---- Route calculation ----
if compute:
    if not st.session_state.start_point or not st.session_state.end_point:
        st.error("Please select both Start and End points.")
    else:
        start_lat, start_lon = st.session_state.start_point
        end_lat, end_lon = st.session_state.end_point

        st.info("Calculating routes...")

        # Find nearest nodes
        orig = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
        dest = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)

        # Add edge costs
        for u, v, data in G.edges(data=True):
            length = data.get("length", 1)
            data["cost_shortest"] = length
            data["cost_shaded"] = length * (1 + alpha / 100)

        # Shortest + shaded routes
        route_shortest = nx.shortest_path(G, orig, dest, weight="cost_shortest")
        route_shaded   = nx.shortest_path(G, orig, dest, weight="cost_shaded")

        st.success("✅ Routes calculated")

        # ---- Show result on map ----
        rm = leafmap.Map(center=[start_lat, start_lon], zoom=15)
        rm.add_basemap("OpenStreetMap")

        # Convert node lists to lat/lon
        shortest_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_shortest]
        shaded_coords   = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_shaded]

        rm.add_polyline(locations=shortest_coords, color="red", weight=5)
        rm.add_polyline(locations=shaded_coords, color="green", weight=5)

        rm.add_marker([start_lat, start_lon], popup="Start")
        rm.add_marker([end_lat, end_lon], popup="End")

        rm.to_streamlit(height=600)


