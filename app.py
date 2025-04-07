import pandas as pd
import geopandas as gpd
import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import re

# Load data
datos = pd.read_csv("Consulta_Ventas_de_Gas_Natural_Comprimido_Vehicular__AUTOMATIZADO__20250316.csv")

# Clean department and municipality names
datos['DEPARTAMENTO'] = datos['DEPARTAMENTO'].str.replace(' ', '_')
datos['MUNICIPIO'] = datos['MUNICIPIO'].str.replace(' ', '_')

# Aggregate data by department
tabla_departamentos = datos.groupby('DEPARTAMENTO').agg({
    'CANTIDAD_VOLUMEN_SUMINISTRADO': 'sum',
    'NUMERO_DE_VENTAS': 'sum',
    'VEHICULOS_ATENDIDOS': 'sum'
}).reset_index().sort_values('CANTIDAD_VOLUMEN_SUMINISTRADO', ascending=False)

# Load shape file
colombia_map = gpd.read_file("MGN2023_DPTO_POLITICO/MGN_ADM_DPTO_POLITICO.shp")

# Process department names for matching
tabla_departamentos['codigo'] = tabla_departamentos['DEPARTAMENTO'].str.lower()
colombia_map['codigo'] = colombia_map['dpto_cnmbr'].str.lower()

# Fix department names to match between datasets
colombia_map['codigo'] = colombia_map['codigo'].str.replace('bogotá, d.c.', 'bogota_d.c.')
colombia_map['codigo'] = colombia_map['codigo'].str.replace(' ', '_')
colombia_map['codigo'] = colombia_map['codigo'].str.replace('á', 'a')
colombia_map['codigo'] = colombia_map['codigo'].str.replace('í', 'i')
colombia_map['codigo'] = colombia_map['codigo'].str.replace('ó', 'o')

# Join the datasets
colombia_mapa_datos = colombia_map.merge(tabla_departamentos, on='codigo', how='left')

# Create Dash app
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])
server = app.server

# Define layout
app.layout = html.Div([
    html.H1("Volumen Suministrado de GNV por Departamento en Colombia (2021-2025)"),
    
    html.Div([
        html.Div([
            html.H3("Filtros"),
            
            html.Label("Filtrar por volumen suministrado:"),
            dcc.RangeSlider(
                id='range-slider',
                min=colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'].min(),
                max=colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'].max()+10000,
                value=[colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'].min(), 
                       colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'].max()],
                marks={
                    int(colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'].min()): 'Min',
                    int(colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'].max()): 'Max'
                },
                step=1000
            ),
            
            html.Label("Paleta de Colores:"),
            dcc.Dropdown(
                id='color-palette',
                options=[
                    {'label': 'Rojo-Amarillo', 'value': 'YlOrRd'},
                    {'label': 'Azules', 'value': 'Blues'},
                    {'label': 'Verdes', 'value': 'Greens'},
                    {'label': 'Púrpuras', 'value': 'Purples'},
                    {'label': 'Rojos', 'value': 'Reds'},
                    {'label': 'Viridis', 'value': 'viridis'},
                    {'label': 'Magma', 'value': 'magma'}
                ],
                value='YlOrRd'
            ),
            
            dcc.Checklist(
                id='show-labels',
                options=[{'label': 'Mostrar nombres', 'value': 'show'}],
                value=[],
                inline=True
            ),
            
            html.Hr(),
            
            html.Button(
                "Descargar Datos", 
                id="btn-download",
            ),
            dcc.Download(id="download-data"),
            
        ], className="three columns"),
        
        html.Div([
            dcc.Graph(id='choropleth-map')
        ], className="nine columns"),
    ], className="row"),
    
    html.Hr(),
    html.P("Fuente: Datos SICOM y DANE (Marzo 2021 - Marzo 2025)"),
])

# Define callbacks
@app.callback(
    Output('choropleth-map', 'figure'),
    [
        Input('range-slider', 'value'),
        Input('color-palette', 'value'),
        Input('show-labels', 'value')
    ]
)
def update_map(volume_range, color_palette, show_labels):
    # Filter data
    filtered_data = colombia_mapa_datos[
        (colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'] >= volume_range[0]) &
        (colombia_mapa_datos['CANTIDAD_VOLUMEN_SUMINISTRADO'] <= volume_range[1])
    ]
    
    # Create choropleth map
    fig = px.choropleth_mapbox(
        filtered_data, 
        geojson=filtered_data.geometry, 
        locations=filtered_data.index, 
        color='CANTIDAD_VOLUMEN_SUMINISTRADO',
        color_continuous_scale=color_palette,
        mapbox_style="carto-positron",
        zoom=4.5, 
        center={"lat": 4.71, "lon": -74.07},
        opacity=0.7,
        labels={'CANTIDAD_VOLUMEN_SUMINISTRADO': 'Volumen Suministrado'}
    )
    
    # Add department labels if selected
    if 'show' in show_labels:
        fig.add_scattermapbox(
            lat=filtered_data.geometry.centroid.y,
            lon=filtered_data.geometry.centroid.x,
            text=filtered_data['dpto_cnmbr'],
            mode='text',
            textfont=dict(size=10, color='black'),
            hoverinfo='none'
        )
    
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=700
    )
    
    return fig

@app.callback(
    Output("download-data", "data"),
    Input("btn-download", "n_clicks"),
    prevent_initial_call=True,
)
def download_csv(n_clicks):
    return dcc.send_data_frame(tabla_departamentos.to_csv, "GNV_Colombia_datos.csv", index=False)

if __name__ == '__main__':
    app.run_server(debug=True)
