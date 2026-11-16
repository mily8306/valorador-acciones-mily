
import streamlit as st
import yfinance as yf
import pandas as pd
import math
from datetime import datetime, timezone

st.set_page_config(page_title="Valorador de Acciones | Inversiones con Mily",page_icon="📈",layout="centered")
st.markdown("""<style>
.block-container{max-width:850px;padding-top:2rem}
h1,h2,h3{letter-spacing:-.035em}
div[data-testid="stMetric"]{background:#f3f6fa;padding:14px;border-radius:12px}
</style>""",unsafe_allow_html=True)
st.title("Valorador de acciones")
st.caption("INVERSIONES CON MILY · Análisis fundamental automatizado")
st.write("Introduce un ticker. La aplicación consulta los datos disponibles y calcula un rango orientativo de valoración mediante escenarios de beneficios futuros.")
ticker=st.text_input("Ticker bursátil",value="NVDA",max_chars=15).strip().upper()
horizon=st.select_slider("Horizonte de valoración",options=[1,2,3,4,5],value=3,format_func=lambda n:f"{n} año"+("s" if n!=1 else ""))
if st.button("Analizar compañía",type="primary",use_container_width=True):
    if not ticker or not all(c.isalnum() or c in ".-^=" for c in ticker):
        st.error("Introduce un ticker válido.")
        st.stop()
    with st.spinner("Consultando datos financieros..."):
        try:
            info=yf.Ticker(ticker).info
        except Exception as exc:
            st.error("No se pudo obtener información del proveedor. Inténtalo más tarde.")
            st.stop()
    name=info.get("longName") or info.get("shortName") or ticker
    price=info.get("currentPrice") or info.get("regularMarketPrice")
    eps=info.get("trailingEps")
    forward_eps=info.get("forwardEps")
    forward_pe=info.get("forwardPE")
    trailing_pe=info.get("trailingPE")
    growth=info.get("earningsGrowth")
    rev_growth=info.get("revenueGrowth")
    market_cap=info.get("marketCap")
    fcf=info.get("freeCashflow")
    currency=info.get("currency","USD")
    st.subheader(f"{name} ({ticker})")
    st.caption(f"Consulta: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Moneda: {currency} · Datos de Yahoo Finance a través de yfinance; pueden estar retrasados o incompletos.")
    def fmt(v,kind="number"):
        if not isinstance(v,(float,int)) or not math.isfinite(v): return "N/D"
        if kind=="money": return f"{v:,.2f} {currency}"
        if kind=="pct": return f"{v*100:.1f}%"
        if kind=="big": return f"{v/1e9:,.2f} mil M {currency}"
        return f"{v:.1f}x"
    a,b,c=st.columns(3)
    a.metric("Precio actual",fmt(price,"money"))
    b.metric("P/E histórico",fmt(trailing_pe))
    c.metric("P/E forward",fmt(forward_pe))
    a,b,c=st.columns(3)
    a.metric("EPS histórico",fmt(eps,"money"))
    b.metric("EPS esperado",fmt(forward_eps,"money"))
    c.metric("Crec. ingresos",fmt(rev_growth,"pct"))
    a,b,c=st.columns(3)
    a.metric("Capitalización",fmt(market_cap,"big"))
    b.metric("FCF",fmt(fcf,"big"))
    c.metric("FCF yield",fmt(fcf/market_cap,"pct") if isinstance(fcf,(int,float)) and isinstance(market_cap,(int,float)) and market_cap>0 else "N/D")
    st.divider()
    st.subheader("Estimación por escenarios")
    st.write("Se proyecta el EPS del próximo año durante el horizonte elegido y se aplica un P/E terminal. El resultado se descuenta a valor presente. Es una estimación, no un precio objetivo garantizado.")
    if not isinstance(price,(int,float)) or price<=0 or not isinstance(forward_eps,(int,float)) or forward_eps<=0:
        st.warning("No hay precio y EPS forward positivos y verificables para este ticker. No se genera valoración automática para evitar resultados engañosos.")
        st.stop()
    if not isinstance(forward_pe,(int,float)) or forward_pe<=0:
        forward_pe=price/forward_eps
    # Use bounded growth assumptions to prevent extreme extrapolation.
    observed_growth = growth if isinstance(growth,(int,float)) and math.isfinite(growth) else rev_growth
    if not isinstance(observed_growth,(int,float)) or not math.isfinite(observed_growth):
        observed_growth=0.08
        st.info("Crecimiento no disponible: se utiliza 8% como supuesto ilustrativo, no como dato de la compañía.")
    base_growth=max(-0.10,min(0.25,observed_growth))
    base_multiple=max(6,min(35,forward_pe))
    discount=0.10
    st.caption(f"Supuestos automáticos: crecimiento base {base_growth:.1%}, P/E terminal base {base_multiple:.1f}x, tasa de descuento {discount:.0%}. El crecimiento se limita a -10%/+25% y el múltiplo a 6x/35x para reducir extrapolaciones extremas.")
    scenarios=[
        ("Conservador",max(-0.15,base_growth-0.10),max(5,base_multiple*0.70)),
        ("Base",base_growth,base_multiple),
        ("Optimista",min(0.35,base_growth+0.10),min(45,base_multiple*1.20))
    ]
    records=[]
    for label,g,m in scenarios:
        future_eps=forward_eps*((1+g)**max(0,horizon-1))
        future_price=future_eps*m
        fair=future_price/((1+discount)**horizon)
        records.append({"Escenario":label,"Crecimiento EPS":f"{g:.1%}","P/E terminal":f"{m:.1f}x","Valor estimado":round(fair,2),"Diferencia vs. precio":f"{(fair/price-1)*100:+.1f}%"})
    df=pd.DataFrame(records)
    st.dataframe(df,hide_index=True,use_container_width=True,column_config={"Valor estimado":st.column_config.NumberColumn(format=f"%.2f {currency}")})
    base_value=records[1]["Valor estimado"]
    upside=base_value/price-1
    st.metric("Valor estimado · escenario base",fmt(base_value,"money"),f"{upside:+.1%} vs. precio de mercado",delta_color="off")
    if upside < -0.15:
        st.warning("El precio está más de un 15% por encima del valor estimado en el escenario base. Posible valoración exigente bajo estos supuestos.")
    elif upside > 0.15:
        st.success("El precio está más de un 15% por debajo del valor estimado en el escenario base. Posible descuento bajo estos supuestos.")
    else:
        st.info("El precio está dentro de ±15% del escenario base: valoración relativamente cercana a esta estimación.")
    st.write("**Importante:** La clasificación depende totalmente de los supuestos, que no son una predicción de resultados. El modelo no es adecuado para empresas con EPS negativo, REITs, bancos, compañías cíclicas extremas o negocios cuya valoración dependa principalmente de activos o flujos de caja no reflejados por el EPS. Para un análisis profesional, contrasta con DCF, EV/EBITDA, comparables, deuda, dilución y guidance.")
    csv=df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Descargar escenarios CSV",csv,file_name=f"valoracion_{ticker}.csv",mime="text/csv")
st.caption("Herramienta educativa · No constituye recomendación de compra o venta ni asesoramiento financiero personalizado. Los datos del proveedor pueden contener errores.")
