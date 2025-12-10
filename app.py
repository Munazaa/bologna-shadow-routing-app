import streamlit as st
import osmnx as ox
import networkx as nx
from streamlit_folium import st_folium
import folium

st.set_page_config(page_title="Bologna Shadow Routing", layout="wide")
st.title("☀️ Bologna Shadow-aware Routing")

# ===== Load Shadow-Enriched Graph =====
@st.cache_resource
def load_graph():
    return ox.load_graphml("bologna_shadow_graph_15.graphml")

G = load_graph()
st.sidebar.success("Road graph successfully loaded!")

# ===== Sidebar Controls =====
st.sidebar.header("Routing Options")
route_mode = st.sidebar.selectbox("Route mode:", ["Shortest only", "Shaded only", "Both"], index=2)

compute = st.sidebar.button("Compute Route")

# ===== Session state for start/end points =====
if "start_point" not in st.session_state:
    st.session_state.start_point = None
if "end_point" not in st.session_state:
    st.session_state.end_point = None

# ===== Clickable Map =====
st.write("### Click to choose your start and end locations")
center = [44.5015, 11.3340]
m = folium.Map(location=center, zoom_start=15, tiles="cartodbpositron")

# Show markers if already selected
if st.session_state.start_point:
    folium.Marker(st.session_state.start_point, tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
if st.session_state.end_point:
    folium.Marker(st.session_state.end_point, tooltip="End", icon=folium.Icon(color="blue")).add_to(m)

# Capture map click
map_data = st_folium(m, height=500, width=900)

if map_data and map_data["last_clicked"]:
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    # First click → start, second → end, third resets
    if st.session_state.start_point is None:
        st.session_state.start_point = (lat, lon)
    elif st.session_state.end_point is None:
        st.session_state.end_point = (lat, lon)
    else:
        st.session_state.start_point = (lat, lon)
        st.session_state.end_point = None

# Show selected coordinates
st.sidebar.write(f"🟢 Start: {st.session_state.start_point}")
st.sidebar.write(f"🔵 End: {st.session_state.end_point}")

# ===== Routing Logic =====
def route_coords(route):
    return [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]

if compute:
    if not st.session_state.start_point or not st.session_state.end_point:
        st.error("Select both Start and End by clicking on the map.")
    else:
        lat1, lon1 = st.session_state.start_point
        lat2, lon2 = st.session_state.end_point

        st.info("Calculating routes...")

        orig = ox.distance.nearest_nodes(G, X=lon1, Y=lat1)
        dest = ox.distance.nearest_nodes(G, X=lon2, Y=lat2)

        # Compute both routes always
        route_short = nx.shortest_path(G, orig, dest, weight="cost_shortest")
        route_shade = nx.shortest_path(G, orig, dest, weight="cost_shaded")

        rm = folium.Map(location=[lat1, lon1], zoom_start=16, tiles="cartodbpositron")

        if route_mode in ["Shortest only", "Both"]:
            folium.PolyLine(route_coords(route_short), color="red", weight=6, tooltip="Shortest").add_to(rm)

        if route_mode in ["Shaded only", "Both"]:
            folium.PolyLine(route_coords(route_shade), color="green", weight=6, tooltip="Shaded").add_to(rm)

        folium.Marker([lat1, lon1], tooltip="Start", icon=folium.Icon(color="green")).add_to(rm)
        folium.Marker([lat2, lon2], tooltip="End", icon=folium.Icon(color="blue")).add_to(rm)

        st_folium(rm, height=500, width=900)

        st.success("Route computed successfully!")
