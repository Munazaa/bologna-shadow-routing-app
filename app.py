import streamlit as st
from datetime import time, timedelta
import osmnx as ox
import networkx as nx
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Bologna Shadow Routing", layout="wide")
st.title("Bologna Shadow-aware Routing")

# ---- Bologna bounding box (your AOI) ----
north = 44.50776772181009
south = 44.49584275842293
west  = 11.32117165803459
east  = 11.346221029006651

# ---- Session state for storing points ----
if "start_point" not in st.session_state:
    st.session_state["start_point"] = (44.4985, 11.3250)

if "end_point" not in st.session_state:
    st.session_state["end_point"] = (44.5055, 11.3420)

st.sidebar.header("Route settings")

st.sidebar.write("Click on the map, then:")

if st.sidebar.button("Set Start Point"):
    if "clicked_point" in st.session_state:
        st.session_state["start_point"] = st.session_state["clicked_point"]

if st.sidebar.button("Set End Point"):
    if "clicked_point" in st.session_state:
        st.session_state["end_point"] = st.session_state["clicked_point"]

start_lat, start_lon = st.session_state["start_point"]
end_lat, end_lon = st.session_state["end_point"]

st.sidebar.write(f"🟢 Start: {start_lat}, {start_lon}")
st.sidebar.write(f"🔵 End: {end_lat}, {end_lon}")

# ---- Time slider ----
route_time = st.sidebar.slider(
    "Select time (27 July 2025)",
    min_value=time(10, 0),
    max_value=time(20, 0),
    value=time(15, 0),
    step=timedelta(minutes=60)
)

# ---- Alpha slider ----
alpha = st.sidebar.slider(
    "Alpha (sun penalty)",
    min_value=0,
    max_value=500,
    value=50,
    step=10
)

compute = st.sidebar.button("Compute routes")

st.write("### Status")

# ---- Always show map (for clicking) ----
base_map = folium.Map(
    location=[start_lat, start_lon],
    zoom_start=15,
    tiles="OpenStreetMap"
)

# Markers for start/end
folium.Marker([start_lat, start_lon], popup="Start", icon=folium.Icon(color="green")).add_to(base_map)
folium.Marker([end_lat, end_lon], popup="End", icon=folium.Icon(color="blue")).add_to(base_map)

map_data = st_folium(base_map, width=900, height=600)

# Capture clicked point
if map_data is not None:
    if "last_clicked" in map_data and map_data["last_clicked"] is not None:
        lat_clicked = map_data["last_clicked"].get("lat")
        lon_clicked = map_data["last_clicked"].get("lng")

        if lat_clicked is not None and lon_clicked is not None:
            st.session_state["clicked_point"] = (lat_clicked, lon_clicked)

# ---- When button pressed ----
if compute:
    st.write("✅ Loading road network from OpenStreetMap...")

    # Load graph
    G = ox.graph_from_bbox(
        bbox=(north, south, east, west),
        network_type="walk"
    )

    st.write(f"✅ Graph loaded with {len(G.nodes)} nodes and {len(G.edges)} edges")

    # Find nearest nodes
    orig = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
    dest = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)

    # Add edge costs
    for u, v, k, data in G.edges(keys=True, data=True):
        length = data.get("length", 1)
        data["cost_shortest"] = length
        data["cost_shaded"] = length * (1 + alpha/100)

    # Calculate routes
    route_shortest = nx.shortest_path(G, orig, dest, weight="cost_shortest")
    route_shaded   = nx.shortest_path(G, orig, dest, weight="cost_shaded")

    st.success("✅ Routes calculated")

    # Create result map
    result_map = folium.Map(
        location=[start_lat, start_lon],
        zoom_start=15,
        tiles="OpenStreetMap"
    )

    # Draw shortest route
    folium.PolyLine(
        [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_shortest],
        color="red",
        weight=5,
        opacity=0.8,
        tooltip="Shortest route (sunny)"
    ).add_to(result_map)

    # Draw shaded route
    folium.PolyLine(
        [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_shaded],
        color="green",
        weight=5,
        opacity=0.8,
        tooltip="Shadow-friendly route"
    ).add_to(result_map)

    # Start/end markers
    folium.Marker([start_lat, start_lon], popup="Start", icon=folium.Icon(color="green")).add_to(result_map)
    folium.Marker([end_lat, end_lon], popup="End", icon=folium.Icon(color="blue")).add_to(result_map)

    # Show result map
    st_folium(result_map, width=900, height=600)
else:
    st.info("Click on the map, set Start/End points, then click 'Compute routes'.")

