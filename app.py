import streamlit as st
import osmnx as ox
import networkx as nx
from streamlit_folium import st_folium
import folium

st.set_page_config(page_title="Bologna Shadow Routing", layout="wide")
st.title("☀️ Bologna Shadow-aware Routing (15:00 shadows)")

# ===== AOI bounds (your small test area) =====
NORTH = 44.50776772181009
SOUTH = 44.49584275842293
WEST  = 11.32117165803459
EAST  = 11.346221029006651

CENTER_LAT = (NORTH + SOUTH) / 2
CENTER_LON = (WEST + EAST) / 2

# ===== Load shadow-aware graph =====
@st.cache_resource
def load_graph():
    G = ox.load_graphml("bologna_shadow_graph_15.graphml")
    return G

G = load_graph()
st.sidebar.success("Road graph successfully loaded!")

# ===== Sidebar controls =====
st.sidebar.header("Routing Options")

route_mode = st.sidebar.selectbox(
    "Route mode:",
    ["Shortest only", "Shaded only", "Both"],
    index=2,
)

alpha = st.sidebar.slider(
    "Alpha (sun penalty strength)",
    min_value=0,
    max_value=500,
    value=100,
    step=10,
)

compute = st.sidebar.button("Compute Route")

# ===== Session state for points =====
if "start_point" not in st.session_state:
    st.session_state.start_point = None
if "end_point" not in st.session_state:
    st.session_state.end_point = None


# ===== Helpers =====
def point_in_aoi(lat, lon):
    return SOUTH <= lat <= NORTH and WEST <= lon <= EAST


def update_edge_costs(G, alpha):
    """Attach shortest + shaded costs to each edge."""
    for u, v, k, data in G.edges(keys=True, data=True):
        length = data.get("length", 1.0)
        shadow_val = data.get("shadow", 0.0)  # 0–255, higher = more shade
        shade_factor = shadow_val / 255.0
        sun_penalty = (1.0 - shade_factor) * alpha

        data["cost_shortest"] = length
        data["cost_shaded"] = length + sun_penalty


def safe_nearest_node(G, lat, lon, max_dist=300):
    """
    Find nearest node; return None if too far from network.
    Uses SciPy KDTree under the hood.
    """
    node, dist = ox.distance.nearest_nodes(G, X=lon, Y=lat, return_dist=True)
    if dist > max_dist:
        return None
    return node


def route_coords(G, route):
    """Convert a list of node ids to (lat, lon) coordinates."""
    return [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]


# ===== Clickable map =====
st.write("### Click to choose your start and end locations")

m = folium.Map(location=[CENTER_LAT, CENTER_LON], zoom_start=15, tiles="cartodbpositron")

# Draw AOI rectangle so the user sees the valid area
folium.Rectangle(
    bounds=[[SOUTH, WEST], [NORTH, EAST]],
    color="blue",
    weight=2,
    fill=False,
    tooltip="Routing is only available inside this area",
).add_to(m)

# Show current markers
if st.session_state.start_point:
    folium.Marker(
        st.session_state.start_point, tooltip="Start", icon=folium.Icon(color="green")
    ).add_to(m)

if st.session_state.end_point:
    folium.Marker(
        st.session_state.end_point, tooltip="End", icon=folium.Icon(color="blue")
    ).add_to(m)

map_data = st_folium(m, height=500, width=900)

# Handle clicks
if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    if not point_in_aoi(lat, lon):
        st.warning("⚠️ Selected point is outside the AOI. Please click inside the blue rectangle.")
    else:
        if st.session_state.start_point is None:
            st.session_state.start_point = (lat, lon)
        elif st.session_state.end_point is None:
            st.session_state.end_point = (lat, lon)
        else:
            # Reset: third click becomes new start
            st.session_state.start_point = (lat, lon)
            st.session_state.end_point = None

# Show chosen coordinates
st.sidebar.write(f"🟢 Start: {st.session_state.start_point}")
st.sidebar.write(f"🔵 End: {st.session_state.end_point}")

# ===== Routing =====
if compute:
    if not st.session_state.start_point or not st.session_state.end_point:
        st.error("Please click on the map to select both Start and End points.")
    else:
        start_lat, start_lon = st.session_state.start_point
        end_lat, end_lon = st.session_state.end_point

        # Safety check: must still be in AOI
        if not point_in_aoi(start_lat, start_lon) or not point_in_aoi(end_lat, end_lon):
            st.error("Selected points are outside the AOI. Please choose points inside the blue rectangle.")
        else:
            st.info("Computing routes...")

            # Update edge weights for current alpha
            update_edge_costs(G, alpha)

            # Find nearest nodes safely (requires scipy)
            orig = safe_nearest_node(G, start_lat, start_lon)
            dest = safe_nearest_node(G, end_lat, end_lon)

            if orig is None:
                st.error("❌ Start point is too far from the road network. Try another location inside the AOI.")
            elif dest is None:
                st.error("❌ End point is too far from the road network. Try another location inside the AOI.")
            else:
                # Compute routes
                route_short = nx.shortest_path(G, orig, dest, weight="cost_shortest")
                route_shade = nx.shortest_path(G, orig, dest, weight="cost_shaded")

                # New map for result
                rm = folium.Map(location=[start_lat, start_lon], zoom_start=16, tiles="cartodbpositron")

                if route_mode in ["Shortest only", "Both"]:
                    folium.PolyLine(
                        route_coords(G, route_short),
                        color="red",
                        weight=6,
                        tooltip="Shortest route",
                    ).add_to(rm)

                if route_mode in ["Shaded only", "Both"]:
                    folium.PolyLine(
                        route_coords(G, route_shade),
                        color="green",
                        weight=6,
                        tooltip="Shaded route",
                    ).add_to(rm)

                folium.Marker(
                    [start_lat, start_lon], tooltip="Start", icon=folium.Icon(color="green")
                ).add_to(rm)
                folium.Marker(
                    [end_lat, end_lon], tooltip="End", icon=folium.Icon(color="blue")
                ).add_to(rm)

                st_folium(rm, height=500, width=900)
                st.success("✅ Routes computed.")
else:
    st.info("Click inside the blue AOI, set Start and End, then click 'Compute Route'.")
