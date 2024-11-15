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

# Load Data
data_file = "updated_dodge_data_with_coordinates.xlsx"  # Assume file is in the same directory
data = pd.read_excel(data_file)

# Extract totals row
totals = data[data["Location"].str.contains("total", case=False, na=False)].iloc[0]

# Preprocess Data
data = data.dropna(subset=["Latitude", "Longitude"])
data["Location"] = data["Location"].str.title()  # Convert locations to Camel Case

# Extract unique generation names (e.g., "Gen IX")
generations = sorted(
    list({col.split()[1] for col in data.columns if "Gen" in col}),
    key=roman_to_int,
    reverse=True
)

# Streamlit App
st.title("Dodge Family Migration Dashboard")

# Sidebar: Select Generation
selected_generation = st.sidebar.selectbox("Select Generation", generations)

# Identify the corresponding columns for births and deaths
birth_col = f"Gen {selected_generation} Born"
death_col = f"Gen {selected_generation} Died"

# Filter Data for the Selected Generation
filtered_data = data[[birth_col, death_col, "Location", "Latitude", "Longitude"]].copy()
filtered_data = filtered_data[(filtered_data[birth_col] > 0) | (filtered_data[death_col] > 0)]

# Add toggles for markers
show_birth_markers = st.checkbox("Show Birth Markers", value=True)
show_death_markers = st.checkbox("Show Death Markers", value=True)

# Interactive Map
st.header(f"Migration Map for Gen {selected_generation}")
m = folium.Map(location=[filtered_data["Latitude"].mean(), filtered_data["Longitude"].mean()], zoom_start=2)

# Marker clusters for births and deaths
if show_birth_markers:
    birth_cluster = MarkerCluster(name="Births").add_to(m)
if show_death_markers:
    death_cluster = MarkerCluster(name="Deaths").add_to(m)

# Add markers for births and deaths
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

# Add heatmaps for births and deaths
if st.checkbox("Show Births Heatmap"):
    heat_data_births = [
        [row["Latitude"], row["Longitude"]]
        for _, row in filtered_data.fillna(0).iterrows()
        for _ in range(int(row[birth_col]))
    ]
    HeatMap(heat_data_births, name="Births Heatmap", radius=15, gradient={0.4: "blue", 0.6: "lime", 1.0: "green"}).add_to(m)

if st.checkbox("Show Deaths Heatmap"):
    heat_data_deaths = [
        [row["Latitude"], row["Longitude"]]
        for _, row in filtered_data.fillna(0).iterrows()
        for _ in range(int(row[death_col]))
    ]
    HeatMap(heat_data_deaths, name="Deaths Heatmap", radius=15, gradient={0.4: "orange", 0.6: "red", 1.0: "darkred"}).add_to(m)

# Add layer control
folium.LayerControl().add_to(m)

# Display the map
st_folium(m, width=700)

# Bar chart for births and deaths at each location
st.header(f"Births and Deaths by Location for Gen {selected_generation}")
chart_data = filtered_data[["Location", birth_col, death_col]].copy()
chart_data.columns = ["Location", "Births", "Deaths"]

fig = px.bar(
    chart_data.melt(id_vars="Location", var_name="Type", value_name="Count"),
    x="Location",
    y="Count",
    color="Type",
    title=f"Births and Deaths by Location for Gen {selected_generation}",
    labels={"Location": "Location", "Count": "Count", "Type": "Type"},
)
st.plotly_chart(fig)

# Additional Insights
st.header("Details for Selected Generation")

# Replace <NA> with 0 and round to whole numbers only for numeric columns
chart_data_cleaned = chart_data.copy()
chart_data_cleaned[["Births", "Deaths"]] = chart_data_cleaned[["Births", "Deaths"]].fillna(0).round(0).astype(int)

# Add a totals row
totals_row = pd.DataFrame({
    "Location": ["Total"],
    "Births": [chart_data_cleaned["Births"].sum()],
    "Deaths": [chart_data_cleaned["Deaths"].sum()]
})
chart_data_cleaned = pd.concat([chart_data_cleaned, totals_row], ignore_index=True)

# Display the table
st.table(chart_data_cleaned)
