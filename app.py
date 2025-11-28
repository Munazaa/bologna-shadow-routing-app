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

# ---- Sidebar inputs ----
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

st.write("### Status")

if compute:
    st.write("✅ Loading road network from OpenStreetMap...")

    # Load graph
    G = ox.graph_from_bbox(north, south, east, west, network_type="walk")
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

    # ---- Create Folium map ----
    m = folium.Map(
        location=[start_lat, start_lon],
        zoom_start=15,
        tiles="OpenStreetMap"
    )

    # Plot shortest route (red)
    folium.PolyLine(
        [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_shortest],
        color="red",
        weight=5,
        opacity=0.8,
        tooltip="Shortest route (sunny)"
    ).add_to(m)

    # Plot shaded route (green)
    folium.PolyLine(
        [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_shaded],
        color="green",
        weight=5,
        opacity=0.8,
        tooltip="Shadow-friendly route"
    ).add_to(m)

    # Start/end markers
    folium.Marker([start_lat, start_lon], popup="Start", icon=folium.Icon(color="blue")).add_to(m)
    folium.Marker([end_lat, end_lon], popup="End", icon=folium.Icon(color="orange")).add_to(m)

    # Show the map
    st_folium(m, width=900, height=600)

else:
    st.info("Set parameters and click 'Compute routes'.")
