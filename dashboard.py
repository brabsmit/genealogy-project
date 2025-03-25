import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, HeatMap
import plotly.express as px

# Helper Function: Convert Roman Numerals to Integers
def roman_to_int(roman):
    roman_dict = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    prev_value = 0
    for char in reversed(roman):
        value = roman_dict[char]
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value
    return total

# ------------------------
# Load and Preprocess Data
# ------------------------
data_file = "updated_dodge_data_with_coordinates.xlsx"  # Assume file is in the same directory
data = pd.read_excel(data_file)

# Extract totals row (if present)
totals = data[data["Location"].str.contains("total", case=False, na=False)].iloc[0]

# Drop rows without coordinates and format Location as Camel Case
data = data.dropna(subset=["Latitude", "Longitude"])
data["Location"] = data["Location"].str.title()

# Extract unique generation names (e.g., "IX" from "Gen IX Born")
generations = sorted(
    list({col.split()[1] for col in data.columns if "Gen" in col}),
    key=roman_to_int,
    reverse=True
)

# ------------------------
# Main Dashboard Interface
# ------------------------
st.title("Dodge Family Migration Dashboard")

# Sidebar: Select Generation and Options
selected_generation = st.sidebar.selectbox("Select Generation", generations)
with st.sidebar.expander("View Options"):
    show_birth_markers = st.checkbox("Show Birth Markers", value=True)
    show_death_markers = st.checkbox("Show Death Markers", value=True)
    show_birth_heatmap = st.checkbox("Show Births Heatmap", value=False)
    show_death_heatmap = st.checkbox("Show Deaths Heatmap", value=False)

# Identify corresponding columns for births and deaths for selected generation
birth_col = f"Gen {selected_generation} Born"
death_col = f"Gen {selected_generation} Died"

# Filter data for the selected generation (locations with at least one birth or death)
filtered_data = data[[birth_col, death_col, "Location", "Latitude", "Longitude"]].copy()
filtered_data = filtered_data[(filtered_data[birth_col] > 0) | (filtered_data[death_col] > 0)]

# ------------------------
# Interactive Map Section
# ------------------------
st.header(f"Migration Map for Gen {selected_generation}")
map_expanded = st.checkbox("Expand Map", value=False)
m = folium.Map(location=[filtered_data["Latitude"].mean(), filtered_data["Longitude"].mean()], zoom_start=2)

# Add marker clusters if toggles are enabled
if show_birth_markers:
    birth_cluster = MarkerCluster(name="Births").add_to(m)
if show_death_markers:
    death_cluster = MarkerCluster(name="Deaths").add_to(m)

# Add markers to clusters based on births and deaths counts
for _, row in filtered_data.iterrows():
    if show_birth_markers and row[birth_col] > 0:
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"Location: {row['Location']}<br>Births: {row[birth_col]}",
            icon=folium.Icon(color="green", icon="info-sign"),
        ).add_to(birth_cluster)
    if show_death_markers and row[death_col] > 0:
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"Location: {row['Location']}<br>Deaths: {row[death_col]}",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(death_cluster)

# Add heatmaps if toggled
if show_birth_heatmap:
    heat_data_births = [
        [row["Latitude"], row["Longitude"]]
        for _, row in filtered_data.fillna(0).iterrows()
        for _ in range(int(row[birth_col]))
    ]
    HeatMap(heat_data_births, name="Births Heatmap", radius=15, 
            gradient={0.4: "blue", 0.6: "lime", 1.0: "green"}).add_to(m)
if show_death_heatmap:
    heat_data_deaths = [
        [row["Latitude"], row["Longitude"]]
        for _, row in filtered_data.fillna(0).iterrows()
        for _ in range(int(row[death_col]))
    ]
    HeatMap(heat_data_deaths, name="Deaths Heatmap", radius=15, 
            gradient={0.4: "orange", 0.6: "red", 1.0: "darkred"}).add_to(m)

# Add layer control to allow toggling different layers
folium.LayerControl().add_to(m)

# Display map according to expansion toggle
if map_expanded:
    st_folium(m, width=None, height=700)  # Full-screen view
else:
    st_folium(m, width=700, height=400)   # Default view

# ------------------------
# Bar Chart Section
# ------------------------
st.header(f"Births and Deaths by Location for Gen {selected_generation}")
chart_data = filtered_data[["Location", birth_col, death_col]].copy()
chart_data.columns = ["Location", "Births", "Deaths"]

fig_bar = px.bar(
    chart_data.melt(id_vars="Location", var_name="Type", value_name="Count"),
    x="Location",
    y="Count",
    color="Type",
    title=f"Births and Deaths by Location for Gen {selected_generation}",
    labels={"Location": "Location", "Count": "Count", "Type": "Type"},
)
st.plotly_chart(fig_bar)

# ------------------------
# Details Table Section
# ------------------------
st.header("Details for Selected Generation")
chart_data_cleaned = chart_data.copy()
chart_data_cleaned[["Births", "Deaths"]] = chart_data_cleaned[["Births", "Deaths"]].fillna(0).round(0).astype(int)
totals_row = pd.DataFrame({
    "Location": ["Total"],
    "Births": [chart_data_cleaned["Births"].sum()],
    "Deaths": [chart_data_cleaned["Deaths"].sum()]
})
chart_data_cleaned = pd.concat([chart_data_cleaned, totals_row], ignore_index=True)
st.dataframe(chart_data_cleaned, height=300)

# ------------------------
# Interactive Timeline Tile
# ------------------------
st.header("Interactive Timeline of Births by Location")

# Convert wide-form data to long-form for timeline animation
timeline_data = []
for idx, row in data.iterrows():
    if "Total" in str(row["Location"]):
        continue  # Skip totals row if present
    for gen in generations:
        birth_val = row.get(f"Gen {gen} Born", 0)
        death_val = row.get(f"Gen {gen} Died", 0)
        timeline_data.append({
            "Location": row["Location"],
            "Latitude": row["Latitude"],
            "Longitude": row["Longitude"],
            "Generation": gen,
            "Births": birth_val,
            "Deaths": death_val,
        })

timeline_df = pd.DataFrame(timeline_data)
timeline_df["Births"] = timeline_df["Births"].fillna(0)

fig_timeline = px.scatter_geo(
    timeline_df,
    lat="Latitude",
    lon="Longitude",
    size="Births",
    hover_name="Location",
    animation_frame="Generation",
    title="Timeline: Births by Location Across Generations",
    projection="natural earth",
    size_max=20
)
st.plotly_chart(fig_timeline, use_container_width=True)

# ------------------------
# Additional Charts & Graphs
# ------------------------
st.header("Additional Charts and Graphs")

# 1. Time Series Line Chart: Using totals row to show births and deaths across generations
time_series_data = []
for gen in generations:
    b_val = totals.get(f"Gen {gen} Born", 0)
    d_val = totals.get(f"Gen {gen} Died", 0)
    time_series_data.append({"Generation": gen, "Births": b_val, "Deaths": d_val})
time_series_df = pd.DataFrame(time_series_data)
# For clarity, you might want to sort generations chronologically (oldest to youngest)
# Here we assume our 'generations' list is in the desired order.
fig_line = px.line(time_series_df, x="Generation", y=["Births", "Deaths"], markers=True,
                   title="Births and Deaths Across Generations")
st.plotly_chart(fig_line, use_container_width=True)

# 3. Donut Chart: Distribution of Births by Location for selected generation
fig_donut = px.pie(chart_data, names="Location", values="Births",
                   title=f"Distribution of Births by Location for Gen {selected_generation}",
                   hole=0.4)
st.plotly_chart(fig_donut, use_container_width=True)

# 4. Sunburst Chart: Hierarchical view of births by Generation and Location
fig_sunburst = px.sunburst(timeline_df, path=['Generation', 'Location'], values='Births',
                           title="Births by Generation and Location")
st.plotly_chart(fig_sunburst, use_container_width=True)

# 5. Bubble Chart: Comparing Births vs. Deaths for selected generation
bubble_chart_data = chart_data.copy()
bubble_chart_data[["Births", "Deaths"]] = bubble_chart_data[["Births", "Deaths"]].fillna(0)
fig_bubble = px.scatter(
    bubble_chart_data,
    x="Births",
    y="Deaths",
    size="Births",
    color="Deaths",
    hover_name="Location",
    title=f"Births vs Deaths for Gen {selected_generation}"
)
st.plotly_chart(fig_bubble, use_container_width=True)
