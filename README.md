# Valorador de acciones — Inversiones con Mily

Aplicación web en español: el visitante introduce **solo un ticker** y obtiene métricas fundamentales y una valoración estimada por escenarios.

## Publicarla y compartir un enlace
1. Crea un repositorio de GitHub y sube `app.py` y `requirements.txt`.
2. Abre https://share.streamlit.io/ e inicia sesión.
3. Selecciona **Create app**, el repositorio y `app.py`; pulsa **Deploy**.
4. Copia la URL pública que te asigne Streamlit y compártela en tu comunidad.

## Ejecutar localmente
`pip install -r requirements.txt`
`streamlit run app.py`

## Metodología y limitaciones
- Datos: `yfinance`, sin clave de API. Su disponibilidad, licencia, límites y estabilidad dependen del proveedor. Verifica los términos de uso antes de ofrecer el servicio públicamente.
- Usa EPS forward, crecimiento reportado, P/E forward y descuento del 10% para calcular escenarios conservador, base y optimista.
- No es un DCF ni un valor intrínseco demostrado. Los supuestos pueden cambiar materialmente el resultado.
- No presenta valoración si faltan precio o EPS forward positivo.
- Es menos adecuado para bancos, REITs, empresas sin ganancias y negocios cíclicos.
- Requiere conexión a internet en el servidor y puede fallar por límites o cambios de Yahoo Finance.
