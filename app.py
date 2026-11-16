import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime,timezone
import math

st.set_page_config(page_title="Valorador | Inversiones con Mily",page_icon="📈",layout="wide")
st.title("Valorador de acciones")
st.caption("INVERSIONES CON MILY · Análisis fundamental")
st.write("Introduce un ticker. El resultado es una estimación por escenarios, no un precio objetivo garantizado.")
def num(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (TypeError,ValueError):return None
def fmt(x,unit=""):
    return "N/D" if x is None else f"{x:,.2f}{unit}"
def big(x):
    if x is None:return "N/D"
    if abs(x)>=1e12:return f"{x/1e12:,.2f} billones"
    if abs(x)>=1e9:return f"{x/1e9:,.2f} mil millones"
    if abs(x)>=1e6:return f"{x/1e6:,.2f} millones"
    return f"{x:,.0f}"
def percent(x):
    return "N/D" if x is None else f"{x*100:.2f}%"
@st.cache_data(ttl=900,show_spinner=False)
def fetch(t):
    q=yf.Ticker(t)
    return q.info or {},q.cashflow
t=st.text_input("Ticker",value="GOOG").strip().upper()
if not t or not all(c.isalnum() or c in ".-^=" for c in t):
    st.warning("Introduce un ticker válido.");st.stop()
try:
    with st.spinner("Consultando datos..."):
        i,cf=fetch(t)
except Exception:
    st.error("El proveedor no respondió. Vuelve a intentar más tarde.");st.stop()
if not i.get("shortName") and not i.get("longName"):
    st.error("Ticker no encontrado.");st.stop()
name=i.get("longName") or i.get("shortName")
currency=i.get("currency") or "USD"
price=num(i.get("currentPrice")) or num(i.get("regularMarketPrice"))
eps=num(i.get("trailingEps"))
fwd=num(i.get("forwardEps"))
pe=num(i.get("trailingPE"))
fpe=num(i.get("forwardPE"))
growth=num(i.get("earningsGrowth"))
rev=num(i.get("revenueGrowth"))
cap=num(i.get("marketCap"))
fcf=num(i.get("freeCashflow"))
st.subheader(f"{name} ({t})")
st.caption(f"Datos Yahoo Finance / yfinance · Consulta {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · {currency}. Datos sujetos a errores, ajustes y retrasos.")
metrics=[
("Precio",fmt(price," "+currency)),("P/E histórico",fmt(pe,"x")),
("P/E forward",fmt(fpe,"x")),("EPS forward",fmt(fwd," "+currency)),
("Crec. ingresos reportado",percent(rev)),("Crec. ganancias reportado",percent(growth)),
("Capitalización",big(cap)+" "+currency),("FCF yield",percent(fcf/cap) if fcf is not None and cap and cap>0 else "N/D")]
for start in (0,4):
    cols=st.columns(4)
    for col,(label,value) in zip(cols,metrics[start:start+4]):col.metric(label,value)
with st.expander("Calidad y fuente del flujo de caja libre"):
    st.write(f"FCF del resumen del proveedor: **{big(fcf)} {currency}**. Su período puede no coincidir con el EPS.")
    if cf is not None and not cf.empty:
        keys=[k for k in cf.index if str(k).replace(" ","").lower()=="freecashflow"]
        if keys:
            data=[{"Fecha":str(c)[:10],"FCF anual":num(cf.loc[keys[0],c])} for c in cf.columns]
            st.dataframe(pd.DataFrame(data),hide_index=True)
            annual=num(cf.loc[keys[0],cf.columns[0]])
            if fcf is not None and annual is not None and abs(fcf-annual)>0.2*max(abs(annual),1):
                st.warning("FCF resumen y FCF anual difieren más de 20%; pueden cubrir períodos diferentes. Verifica el reporte original.")
    st.caption("Un FCF negativo no se reemplaza por cero ni se interpreta automáticamente como un error.")
st.divider()
st.subheader("Valoración por escenarios")
st.write("Modelo: EPS forward proyectado × P/E terminal, descontado al presente. No es un DCF.")
if price is None or price<=0 or fwd is None or fwd<=0:
    st.warning("No se puede valorar automáticamente: faltan precio o EPS forward positivos.");st.stop()
if growth is None:
    base_g=8.0
    st.warning("No hay crecimiento de ganancias disponible. Se propone 8% ilustrativo, NO consenso de analistas.")
else:
    base_g=round(max(-10,min(25,growth*100)),1)
    st.info(f"Crecimiento de ganancias reportado: {growth*100:.1f}%. NO es una proyección multianual. El supuesto inicial está limitado a -10%/+25% y puede editarse.")
base_pe=max(6,min(35,fpe if fpe and fpe>0 else price/fwd))
with st.expander("Editar supuestos",expanded=True):
    a,b,c=st.columns(3)
    years=a.slider("Horizonte (años)",1,5,3)
    rate=b.number_input("Descuento anual (%)",0.,40.,10.,0.5)/100
    margin=c.slider("Margen de seguridad (%)",0,50,20)/100
    a,b,c=st.columns(3)
    gb=a.number_input("Crecimiento conservador (%)",-50.,100.,float(max(-20,base_g-10)),1.)
    gm=b.number_input("Crecimiento base (%)",-50.,100.,float(base_g),1.)
    go=c.number_input("Crecimiento optimista (%)",-50.,100.,float(min(40,base_g+10)),1.)
    a,b,c=st.columns(3)
    pb=a.number_input("P/E conservador",1.,150.,float(round(max(5,base_pe*.7),1)),.5)
    pm=b.number_input("P/E base",1.,150.,float(round(base_pe,1)),.5)
    po=c.number_input("P/E optimista",1.,150.,float(round(min(45,base_pe*1.2),1)),.5)
if gb>gm or gm>go or pb>pm or pm>po:
    st.warning("Los escenarios no están ordenados. Revisa crecimiento y P/E.")
def value(g,p):
    return fwd*(1+g/100)**(years-1)*p/(1+rate)**years
rows=[]
for label,g,p in [("Conservador",gb,pb),("Base",gm,pm),("Optimista",go,po)]:
    v=value(g,p)
    rows.append({"Escenario":label,"Crecimiento EPS":f"{g:.1f}%","P/E terminal":f"{p:.1f}x","Valor estimado":round(v,2),"Diferencia vs. precio":f"{v/price-1:+.1%}","Entrada con margen":round(v*(1-margin),2)})
st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
v=value(gm,pm)
a,b=st.columns(2)
a.metric("Valor base estimado",fmt(v," "+currency),f"{v/price-1:+.1%} vs. mercado",delta_color="off")
b.metric("Precio con margen de seguridad",fmt(v*(1-margin)," "+currency))
if price>v*1.15:st.warning("Valoración exigente bajo los supuestos seleccionados; no es una señal de venta.")
elif price<v*.85:st.info("Posible descuento bajo los supuestos seleccionados; no es una señal de compra.")
else:st.info("Precio relativamente cercano al escenario base bajo los supuestos seleccionados.")
with st.expander("Sensibilidad: crecimiento vs. P/E"):
    st.dataframe(pd.DataFrame({f"P/E {p:.1f}x":[round(value(g,p),2) for g in (gm-5,gm,gm+5)] for p in (max(1,pm-5),pm,pm+5)},index=[f"Crec. {g:.1f}%" for g in (gm-5,gm,gm+5)]),use_container_width=True)
st.download_button("Descargar escenarios CSV",pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),file_name=f"valoracion_{t}.csv",mime="text/csv")
st.caption("Verifica EPS, guidance, márgenes, CAPEX, deuda, dilución y comparables. El modelo puede ser inadecuado para bancos, REITs, negocios cíclicos y empresas sin beneficios. Uso educativo; no asesoramiento financiero.")
