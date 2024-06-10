from sqlalchemy import text, create_engine
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output


# Constants
DB_NAME = "world_data_bank.sqlite3"
TABLE = "world_data_bank"

countries = {
    "Americas": ["CA", "US", "MX", "BR", "AR", "CL"],
    "Europe": ["GB", "FR", "ES", "DE", "NL", "IT"],
    "Asia": ["IN", "CN", "JP", "PK", "KP", "ID"],
}

labels = {
    "YEAR": "Year",
    "COUNTRY_ID": "Country",
    "POP": "Total Population",
    "POP_GROWTH": "Yearly Population Growth",
    "POP_GROWTH_PER_1000": "Yearly Population Growth (per 1000 people)",
    "BIRTHS_PER_1000": "Birth Rate (per 1000 people)",
    "DEATHS_PER_1000": "Death Rate (per 1000 people)",
    "DEATHS": "Total Deaths",
    "CA": "Canada",
    "US": "USA",
    "MX": "Mexico",
    "BR": "Brazil",
    "AR": "Argentina",
    "CL": "Chile",
    "GB": "Great Britain",
    "FR": "France",
    "ES": "Spain",
    "DE": "Germany",
    "IT": "Italy",
    "NL": "Netherlands",
    "IN": "India",
    "CH": "China",
    "ID": "Indonesia",
    "JP": "Japan",
    "KP": "Korea",
    "PK": "Pakistan",
}

# SQL Quearys
queary_pop_and_growth_all = f"""
WITH temp AS
(
  SELECT
    COUNTRY_ID,
    DATE AS YEAR,
    VALUE AS POP,
    VALUE / 1000 AS POP_DIV_1000,
    VALUE - LAG(VALUE)
      OVER(PARTITION BY COUNTRY_ID ORDER BY DATE)
      AS POP_GROWTH
  FROM {TABLE}
  WHERE INDICATOR_ID = "SP.POP.TOTL"
  ORDER BY COUNTRY_ID, YEAR
)
SELECT
  COUNTRY_ID,
  YEAR,
  POP,
  POP_GROWTH,
  POP_GROWTH / POP_DIV_1000 AS POP_GROWTH_PER_1000
FROM temp
WHERE temp.POP_GROWTH IS NOT NULL
"""

queary_pop_growth_birth_and_death = f"""
WITH temp_growth AS
(
  SELECT
    COUNTRY_ID,
    DATE AS YEAR,
    VALUE AS POP,
    VALUE - LAG(VALUE)
      OVER(PARTITION BY COUNTRY_ID ORDER BY DATE)
      AS POP_GROWTH
  FROM {TABLE}
  WHERE INDICATOR_ID = "SP.POP.TOTL"
),
temp_births AS (
  SELECT
    COUNTRY_ID,
    DATE AS YEAR,
    VALUE AS BIRTHS_PER_1000
  FROM {TABLE}
  WHERE INDICATOR_ID = "SP.DYN.CBRT.IN"
),
temp_deaths AS (
  SELECT
    COUNTRY_ID,
    DATE AS YEAR,
    VALUE AS DEATHS_PER_1000
  FROM {TABLE}
  WHERE INDICATOR_ID = "SP.DYN.CDRT.IN"
)
SELECT
  temp_growth.COUNTRY_ID,
  temp_growth.YEAR,
  temp_growth.POP,
  temp_growth.POP_GROWTH,
  temp_births.BIRTHS_PER_1000,
  temp_deaths.DEATHS_PER_1000
FROM ((temp_growth
LEFT JOIN temp_births
  ON temp_growth.COUNTRY_ID=temp_births.COUNTRY_ID
  AND temp_growth.YEAR=temp_births.YEAR)
LEFT JOIN temp_deaths
  ON temp_growth.COUNTRY_ID=temp_deaths.COUNTRY_ID
  AND temp_growth.YEAR=temp_deaths.YEAR)
WHERE temp_growth.POP_GROWTH IS NOT NULL
  AND temp_growth.YEAR > 2012
ORDER BY temp_growth.COUNTRY_ID, temp_growth.YEAR
"""

queary_deaths_last_5 = f"""
WITH temp_growth AS
(
  SELECT
    COUNTRY_ID,
    DATE AS YEAR,
    VALUE AS POP,
    VALUE / 1000 AS POP_DIV_1000
  FROM {TABLE}
  WHERE INDICATOR_ID = "SP.POP.TOTL"
),
temp_deaths AS (
  SELECT
    COUNTRY_ID,
    DATE AS YEAR,
    VALUE AS DEATHS_PER_1000
  FROM {TABLE}
  WHERE INDICATOR_ID = "SP.DYN.CDRT.IN"
)
SELECT
  temp_growth.COUNTRY_ID,
  temp_growth.YEAR,
  temp_deaths.DEATHS_PER_1000 * temp_growth.POP_DIV_1000 AS DEATHS
FROM temp_growth
LEFT JOIN temp_deaths
  ON temp_growth.COUNTRY_ID=temp_deaths.COUNTRY_ID
  AND temp_growth.YEAR=temp_deaths.YEAR
WHERE temp_growth.YEAR > 2017
  AND temp_deaths.DEATHS_PER_1000 IS NOT NULL
ORDER BY temp_growth.COUNTRY_ID, temp_growth.YEAR
"""


# Helpers
def queary_db(db, queary):
    en = create_engine(f"sqlite:///{db}")
    with en.connect() as conn:
        result = conn.execute(text(queary))
    return pd.DataFrame(result)


def to_mil_label(n):
    n = n / 1000000
    if n < 1:
        return f"{n:.2f}M"
    else:
        return f"{n:.1f}M"


# Plot North America Versus Pop Growth ########################################

pop_growth_all_df = queary_db(DB_NAME, queary_pop_and_growth_all)

years = [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]
ca_rel_growth = pop_growth_all_df.loc[pop_growth_all_df["COUNTRY_ID"] == "CA"][
    "POP_GROWTH_PER_1000"
]
us_rel_growth = pop_growth_all_df.loc[pop_growth_all_df["COUNTRY_ID"] == "US"][
    "POP_GROWTH_PER_1000"
]
mx_rel_growth = pop_growth_all_df.loc[pop_growth_all_df["COUNTRY_ID"] == "MX"][
    "POP_GROWTH_PER_1000"
]

fig_na_growth = go.Figure()
fig_na_growth.add_trace(
    go.Bar(
        x=years,
        y=ca_rel_growth,
        name="Canada",
        marker_color="firebrick",
    )
)
fig_na_growth.add_trace(
    go.Bar(
        x=years,
        y=us_rel_growth,
        name="USA",
        marker_color="midnightblue",
    )
)
fig_na_growth.add_trace(
    go.Bar(
        x=years,
        y=mx_rel_growth,
        name="Mexico",
        marker_color="forestgreen",
    )
)

fig_na_growth.update_layout(
    title="Yearly Population Growth for North American Countries 2013-2022",
    title_font_size=20,
    barmode="group",
    xaxis_tickangle=-45,
    yaxis_title="Growth Per 1000 People",
    xaxis=dict(title="Year", tickmode="linear"),
)
fig_na_growth.show()


# Plot Birth Rate Vs Death Rate ###############################################

pop_changes_df = queary_db(DB_NAME, queary_pop_growth_birth_and_death)

# Create and show plot
fig_pop_changes = px.scatter(
    pop_changes_df,
    x="BIRTHS_PER_1000",
    y="DEATHS_PER_1000",
    color="COUNTRY_ID",
    title="Birth Rate vs Death Rate 2013-2022",
    hover_name="YEAR",
    labels=labels,
)
fig_pop_changes.show()


# Plot Deaths During 5 Years Around Pandemic ##################################

deaths_last_5_df = queary_db(DB_NAME, queary_deaths_last_5)

# Create and show plot
fig_deaths_last_5 = px.bar(
    deaths_last_5_df,
    title="Total Deaths 2018-2022",
    x="YEAR",
    y="DEATHS",
    color="COUNTRY_ID",
    labels=labels,
)
fig_deaths_last_5.show()


# Interactive Plot Region Population Growth ###################################

pop_types = {
    "Total Population": "POP",
    "Yearly Growth": "POP_GROWTH",
    "Relative Yearly Growth": "POP_GROWTH_PER_1000",
}

pop_app = Dash(__name__)

pop_app.layout = html.Div(
    [
        html.H4("Country Population Growth 2001-2022"),
        dcc.Dropdown(
            id="region_dd",
            options=["Americas", "Europe", "Asia"],
            value="Americas",
            clearable=False,
        ),
        dcc.Dropdown(
            id="pop_type_dd",
            options=[
                "Total Population",
                "Yearly Growth",
                "Relative Yearly Growth",
            ],
            value="Total Population",
            clearable=False,
        ),
        dcc.Graph(id="graph"),
    ]
)


@pop_app.callback(
    Output("graph", "figure"),
    Input("region_dd", "value"),
    Input("pop_type_dd", "value"),
)
def update_line_chart(region, pop_type):
    df = pop_growth_all_df
    mask = df["COUNTRY_ID"].isin(countries[region])
    y_type = pop_types[pop_type]
    fig = px.line(
        df[mask],
        x="YEAR",
        labels=labels,
        y=y_type,
        color="COUNTRY_ID",
        markers=True,
    )
    return fig


pop_app.run_server(debug=True)
