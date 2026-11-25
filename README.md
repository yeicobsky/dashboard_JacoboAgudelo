# Dashboard de logs

Proyecto final de Analítica de Datos (UCP 2026-2).

Es un dashboard hecho con Dash que muestra información de los logs de varios microservicios guardados en una base de datos PostgreSQL. Se puede filtrar por servicio y por fechas, y muestra el total de peticiones, el porcentaje de errores, la duración de las peticiones, los endpoints más lentos y los errores más comunes.

## Cómo usarlo

1. Clonar el repositorio:

```
git clone https://github.com/yeicobsky/dashboard_JacoboAgudelo.git
cd dashboard_JacoboAgudelo
```

2. Instalar las librerías:

```
pip install -r requirements.txt
```

3. Crear un archivo `.env` en la carpeta del proyecto con la conexión a la base de datos (se puede copiar `.env.example`):

```
DATABASE_URL=postgresql://usuario:contraseña@host:5432/base
```

El `.env` no está en el repositorio porque tiene la contraseña.

4. Ejecutar:

```
python app.py
```

5. Abrir http://127.0.0.1:8050/ en el navegador.

## Notas

- Las horas están en hora de Colombia.
- Los datos se cargan cuando se inicia la app, así que para ver los logs nuevos hay que reiniciarla.

Jacobo Agudelo Acevedo