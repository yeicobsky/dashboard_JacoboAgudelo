import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from dash import Dash, html, dash_table

#Conexión
load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

#Explorar la tabla logs
insp = inspect(engine)
columnas = insp.get_columns("logs", schema="public")

with engine.connect() as conn:
    total = conn.execute(text("SELECT COUNT(*) FROM public.logs")).scalar()

muestra = pd.read_sql("SELECT * FROM public.logs LIMIT 50", engine)

# También en la consola
print("Total de registros:", total)
for col in columnas:
    print(f"  {col['name']}: {col['type']}")
print(muestra.head(10).to_string())

#Dashboard
app = Dash()

app.layout = html.Div(children=[
    html.H1('Dashboard Logs'),
    html.P(f'Total de registros en la tabla: {total:,}'),

    html.H3('Columnas'),
    html.Ul([html.Li(f"{c['name']} ({c['type']})") for c in columnas]),

    html.H3('Primeras 50 filas'),
    dash_table.DataTable(
        data=muestra.astype(str).to_dict('records'),
        columns=[{'name': c, 'id': c} for c in muestra.columns],
        page_size=15,
        sort_action='native',
        filter_action='native',
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'fontSize': 13, 'padding': '4px'},
    ),
])

if __name__ == '__main__':
    app.run(debug=True)