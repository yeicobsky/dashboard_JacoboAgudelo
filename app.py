import os
import numpy as np
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from dash import Dash, html, dcc, dash_table, callback, Output, Input

#Conexión
load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

#Explorar la tabla logs
insp = inspect(engine)
columnas = insp.get_columns("logs", schema="public")


logs = pd.read_sql("SELECT * FROM public.logs", engine)

#Conversion de zona horaria a America/Bogota
ZONA = "America/Bogota"  
logs["ts"] = logs["ts"].dt.tz_convert(ZONA)
logs["ingested_at"] = logs["ingested_at"].dt.tz_convert(ZONA)

#Columnas nuevas
logs["nivel"] = logs["log"].str.extract(r"\s(INFO|WARN|ERROR|DEBUG)\s", expand=False).fillna("OTRO")
logs["mensaje"] = logs["log"].str.extract(r"duration=\d+ms\s+(.*)$", expand=False).fillna("")
logs["clase_status"] = (logs["status_code"] // 100).astype(int).astype(str) + "xx"
logs["endpoint"] = logs["http_method"] + " " + logs["url"]
logs["latencia_ingesta_ms"] = (logs["ingested_at"] - logs["ts"]).dt.total_seconds() * 1000
logs["hora"] = logs["ts"].dt.floor("h")
logs["fecha"] = logs["ts"].dt.date

#Variables para filtros
SERVICIOS = ["Todos"] + sorted(logs["svc"].unique())
FECHA_MIN = logs["fecha"].min()
FECHA_MAX = logs["fecha"].max()

print(f"Registros cargados: {len(logs):,} | Servicios: {SERVICIOS[1:]} | {FECHA_MIN} a {FECHA_MAX}")


#Colores
COLOR_ESTADO = {"INFO": "#0ca30c", "WARN": "#fab219", "ERROR": "#d03b3b", "OTRO": "#898781",
                "2xx": "#0ca30c", "3xx": "#2a78d6", "4xx": "#fab219", "5xx": "#d03b3b"}
COLOR_SERIE = "#2a78d6"   # para gráficas de una sola serie
TEXTO = "#52514e"
GRILLA = "#e1e0d9"

#Función de estilo
def estilo(fig, titulo):
    """Estilo común para todas las figuras."""
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=16, color="#0b0b0b")),
        template="plotly_white",
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color=TEXTO),
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(title=None, orientation="h", y=1.02, yanchor="bottom", x=1, xanchor="right"),
        hoverlabel=dict(bgcolor="white"),
        plot_bgcolor="white",
    )
    fig.update_xaxes(gridcolor=GRILLA, linecolor="#c3c2b7", title=None)
    fig.update_yaxes(gridcolor=GRILLA, linecolor="#c3c2b7")
    return fig

#Funcion para filtrar
def filtrar(datos, servicio="Todos", inicio=None, fin=None):
    seleccion = datos
    if servicio != "Todos":
        seleccion = seleccion.loc[seleccion["svc"] == servicio]
    if inicio is not None:
        seleccion = seleccion.loc[seleccion["fecha"] >= pd.Timestamp(inicio).date()]
    if fin is not None:
        seleccion = seleccion.loc[seleccion["fecha"] <= pd.Timestamp(fin).date()]
    return seleccion.copy()

#Estilos de tarjetas KPI y Graficos
TARJETA = {"background": "white", "border": "1px solid #e1e0d9", "borderRadius": "8px",
           "padding": "16px", "flex": "1", "minWidth": "180px"}
FILA = {"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "16px"}


def kpi(id_valor, titulo):
    return html.Div(style=TARJETA, children=[
        html.Div(titulo, style={"fontSize": "13px", "color": TEXTO}),
        html.Div(id=id_valor, style={"fontSize": "28px", "fontWeight": "600", "color": "#0b0b0b"}),
    ])


def resumir(datos):
    total = len(datos)
    errores = int((datos["status_code"] >= 500).sum())
    return {
        "total": total,
        "pct_errores": errores / total * 100 if total else np.nan,
        "mediana_ms": datos["duration"].median() if total else np.nan,
        "p95_ms": datos["duration"].quantile(0.95) if total else np.nan,
    }

#Dashboard
app = Dash()

app.layout = html.Div(
    style={"fontFamily": "Segoe UI, Arial, sans-serif", "background": "#f6f6f4",
           "padding": "24px", "minHeight": "100vh"},
    children=[
        html.H1("Dashboard de logs", style={"margin": "0 0 4px 0"}),
        html.P(f"Peticiones registradas por los microservicios · {FECHA_MIN} a {FECHA_MAX} · hora de Colombia",
               style={"color": TEXTO, "marginTop": 0}),

        # Filtros en una sola fila
        html.Div(style={**FILA, "alignItems": "end"}, children=[
            html.Div(style={"width": "220px"}, children=[
                html.Label("Servicio", style={"fontSize": "13px", "color": TEXTO}),
                dcc.Dropdown(SERVICIOS, "Todos", id="filtro-servicio", clearable=False),
            ]),
            html.Div(children=[
                html.Label("Rango de fechas", style={"fontSize": "13px", "color": TEXTO, "display": "block"}),
                dcc.DatePickerRange(
                    id="filtro-fechas",
                    min_date_allowed=FECHA_MIN, max_date_allowed=FECHA_MAX,
                    start_date=FECHA_MIN, end_date=FECHA_MAX,
                    display_format="YYYY-MM-DD",
                ),
            ]),
        ]),

        # Indicadores
        html.Div(style=FILA, children=[
            kpi("kpi-total", "Peticiones"),
            kpi("kpi-errores", "Errores del servidor (5xx)"),
            kpi("kpi-mediana", "Duración mediana"),
            kpi("kpi-p95", "Duración p95"),
        ]),

        # Gráficas
        html.Div(style={**TARJETA, "marginBottom": "16px"}, children=[dcc.Graph(id="graf-tiempo")]),
        html.Div(style=FILA, children=[
            html.Div(style=TARJETA, children=[dcc.Graph(id="graf-status")]),
            html.Div(style=TARJETA, children=[dcc.Graph(id="graf-endpoints")]),
        ]),

        # Tabla de mensajes de error
        html.Div(style=TARJETA, children=[
            html.H3("Mensajes de error y advertencia más frecuentes", style={"marginTop": 0, "fontSize": "16px"}),
            dash_table.DataTable(
                id="tabla-errores",
                page_size=10,
                sort_action="native",
                style_cell={"textAlign": "left", "fontSize": 13, "padding": "6px",
                            "fontFamily": "Segoe UI, Arial, sans-serif"},
                style_header={"fontWeight": "600", "background": "#f6f6f4"},
            ),
        ]),
    ],
)



#Callback: cada vez que cambia un filtro, se recalcula todo
@callback(
    Output("kpi-total", "children"),
    Output("kpi-errores", "children"),
    Output("kpi-mediana", "children"),
    Output("kpi-p95", "children"),
    Output("graf-tiempo", "figure"),
    Output("graf-status", "figure"),
    Output("graf-endpoints", "figure"),
    Output("tabla-errores", "data"),
    Output("tabla-errores", "columns"),
    Input("filtro-servicio", "value"),
    Input("filtro-fechas", "start_date"),
    Input("filtro-fechas", "end_date"),
)
def actualizar(servicio, inicio, fin):
    datos = filtrar(logs, servicio, inicio, fin)
    r = resumir(datos)

    def fmt(valor, sufijo=""):
        return "—" if pd.isna(valor) else f"{valor:,.0f}{sufijo}"

    kpi_total = fmt(r["total"])
    kpi_errores = "—" if pd.isna(r["pct_errores"]) else f"{r['pct_errores']:.1f} %"
    kpi_mediana = fmt(r["mediana_ms"], " ms")
    kpi_p95 = fmt(r["p95_ms"], " ms")

    #Peticiones por hora, separadas por nivel
    por_hora = (datos.groupby(["hora", "nivel"]).size().reset_index(name="peticiones"))
    fig_tiempo = px.line(
        por_hora, x="hora", y="peticiones", color="nivel",
        color_discrete_map=COLOR_ESTADO,
        category_orders={"nivel": ["INFO", "WARN", "ERROR", "OTRO"]},
        labels={"hora": "Hora", "peticiones": "Peticiones", "nivel": "Nivel"},
    )
    fig_tiempo.update_traces(line=dict(width=2))
    fig_tiempo.update_layout(hovermode="x unified")
    estilo(fig_tiempo, "Peticiones por hora según nivel")

    #Proporción de códigos de estado por servicio
    status = (datos.groupby(["svc", "clase_status"]).size().reset_index(name="peticiones"))
    status["porcentaje"] = status["peticiones"] / status.groupby("svc")["peticiones"].transform("sum") * 100
    fig_status = px.bar(
        status, x="porcentaje", y="svc", color="clase_status", orientation="h",
        color_discrete_map=COLOR_ESTADO,
        category_orders={"clase_status": ["2xx", "3xx", "4xx", "5xx"]},
        labels={"porcentaje": "% de peticiones", "svc": "", "clase_status": "Código"},
        hover_data={"peticiones": ":,", "porcentaje": ":.1f"},
    )
    fig_status.update_traces(marker_line_color="white", marker_line_width=2)
    fig_status.update_xaxes(range=[0, 100], ticksuffix=" %")
    estilo(fig_status, "Códigos de respuesta por servicio")

    #Endpoints más lentos (percentil 95 de la duración)
    endpoints = (datos.groupby("endpoint")["duration"]
                 .agg(p95=lambda s: s.quantile(0.95), peticiones="size")
                 .reset_index().sort_values("p95").tail(10))
    fig_endpoints = px.bar(
        endpoints, x="p95", y="endpoint", orientation="h",
        labels={"p95": "Duración p95 (ms)", "endpoint": ""},
        hover_data={"peticiones": ":,", "p95": ":,.0f"},
        text="p95",
    )
    fig_endpoints.update_traces(marker_color=COLOR_SERIE, texttemplate="%{text:,.0f} ms",
                                textposition="outside", cliponaxis=False)
    estilo(fig_endpoints, "Endpoints más lentos (p95)")
    fig_endpoints.update_layout(margin=dict(r=60))

    #Tabla de mensajes en 4xx / 5xx
    problemas = datos.loc[datos["status_code"] >= 400]
    tabla = (problemas.groupby(["svc", "endpoint", "status_code", "mensaje"]).size()
             .reset_index(name="veces").sort_values("veces", ascending=False))
    tabla["% del total"] = (tabla["veces"] / max(r["total"], 1) * 100).round(2)
    columnas = [
        {"name": "Servicio", "id": "svc"},
        {"name": "Endpoint", "id": "endpoint"},
        {"name": "Código", "id": "status_code"},
        {"name": "Mensaje", "id": "mensaje"},
        {"name": "Veces", "id": "veces"},
        {"name": "% del total", "id": "% del total"},
    ]

    return (kpi_total, kpi_errores, kpi_mediana, kpi_p95,
            fig_tiempo, fig_status, fig_endpoints,
            tabla.to_dict("records"), columnas)

if __name__ == '__main__':
    app.run(debug=True)