import streamlit as st
import osmnx as ox
import networkx as nx
import leafmap.foliumap as leafmap

st.set_page_config(page_title="Bologna Shadow Routing", layout="wide")
st.title("Bologna Shadow-aware Routing (15:00 shadows)")

# ===== Load precomputed shadow-aware graph =====
@st.cache_resource
def load_graph():
    # GraphML file you uploaded to the repo
    G = ox.load_graphml("bologna_shadow_graph_15.graphml")
    return G

G = load_graph()
st.sidebar.success("Road graph loaded.")

# ===== Sidebar controls =====
st.sidebar.header("Route settings")

# Route mode: user chooses
route_mode = st.sidebar.selectbox(
    "Route mode",
    ["Shortest only", "Shaded only", "Both"],
    index=2
)

alpha = st.sidebar.slider(
    "Alpha (sun penalty strength)",
    min_value=0,
    max_value=500,
    value=100,
    step=10,
)

compute = st.sidebar.button("Compute route")

# ===== Session state for points =====
if "start_point" not in st.session_state:
    st.session_state.start_point = None
if "end_point" not in st.session_state:
    st.session_state.end_point = None

# ===== Helper: compute edge costs given alpha =====
def update_edge_costs(G, alpha):
    for u, v, k, data in G.edges(keys=True, data=True):
        length = data.get("length", 1.0)
        shadow_val = data.get("shadow", 0.0)  # 0-255, higher = more shade

        # Normalize to 0–1, where 1 = full shade, 0 = full sun
        shade_factor = shadow_val / 255.0

        # Sun penalty: more sun -> bigger penalty
        sun_penalty = (1.0 - shade_factor) * alpha

        data["cost_shortest"] = length
        data["cost_shaded"] = length + sun_penalty

# ===== Clickable map to choose points =====
st.write("### Click on the map to select start and end points")

# Rough center of your AOI
center_lat = 44.5015
center_lon = 11.3340

m = leafmap.Map(center=[center_lat, center_lon], zoom=15)
m.add_basemap("OpenStreetMap")

# Show current start/end markers
if st.session_state.start_point:
    m.add_marker(list(st.session_state.start_point), popup="Start")
if st.session_state.end_point:
    m.add_marker(list(st.session_state.end_point), popup="End")

clicks = m.to_streamlit(height=500)

# Handle clicks: first click = start, second = end, then overwrite
if clicks and len(clicks) > 0:
    last_click = clicks[-1]  # (lon, lat)
    lat, lon = last_click[1], last_click[0]

    if st.session_state.start_point is None:
        st.session_state.start_point = (lat, lon)
    elif st.session_state.end_point is None:
        st.session_state.end_point = (lat, lon)
    else:
        # Reset and start again
        st.session_state.start_point = (lat, lon)
        st.session_state.end_point = None

# Display chosen coordinates
if st.session_state.start_point:
    st.sidebar.write(f"🟢 Start: {st.session_state.start_point}")
else:
    st.sidebar.info("Click on the map to set Start point.")

if st.session_state.end_point:
    st.sidebar.write(f"🔵 End: {st.session_state.end_point}")
else:
    st.sidebar.info("Click again to set End point.")

# ===== Routing when user clicks "Compute route" =====
if compute:
    if not st.session_state.start_point or not st.session_state.end_point:
        st.error("Please click on the map to set both Start and End points.")
    else:
        start_lat, start_lon = st.session_state.start_point
        end_lat, end_lon = st.session_state.end_point

        st.info("Computing routes...")

        # Update edge costs based on alpha
        update_edge_costs(G, alpha)

        # Find nearest graph nodes
        orig = ox.distance.nearest_nodes(G, X=start_lon, Y=start_lat)
        dest = ox.distance.nearest_nodes(G, X=end_lon, Y=end_lat)

        # Always compute both, then choose what to show
        route_short = nx.shortest_path(G, orig, dest, weight="cost_shortest")
        route_shade = nx.shortest_path(G, orig, dest, weight="cost_shaded")

        # Create result map
        rm = leafmap.Map(center=[start_lat, start_lon], zoom=16)
        rm.add_basemap("OpenStreetMap")

        # Helper to turn nodes into lat/lon coords
        def route_coords(route):
            return [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]

        # Draw according to chosen mode
        if route_mode in ["Shortest only", "Both"]:
            rm.add_polyline(
                locations=route_coords(route_short),
                color="red",
                weight=5,
                popup="Shortest"
            )
        if route_mode in ["Shaded only", "Both"]:
            rm.add_polyline(
                locations=route_coords(route_shade),
                color="green",
                weight=5,
                popup="Shaded"
            )

        rm.add_marker([start_lat, start_lon], popup="Start")
        rm.add_marker([end_lat, end_lon], popup="End")

        rm.to_streamlit(height=500)
        st.success("Routes computed.")
else:
    st.info("Click on the map to set Start/End points, then click 'Compute route'.")



