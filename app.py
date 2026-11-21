import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Ventas 2024 vs 2025", layout="wide")

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
META_PCT = 4.0      # afirmación a verificar
TOLERANCIA = 0.5    # puntos porcentuales para considerarla "aproximadamente correcta"
COLOR_ANIO = {"2024": "#1f77b4", "2025": "#ff7f0e"}


@st.cache_data
def cargar():
    df = pd.read_csv("ventas_mensuales.csv")
    return df[df["anio"].isin([2024, 2025])]


def pct_txt(v):
    return "n/d" if pd.isna(v) else f"{v:.2f}%"


def comparativo_mensual(df, medida):
    comp = (
        df.groupby(["anio", "mes"])[medida].sum().reset_index()
        .pivot(index="mes", columns="anio", values=medida)
        .reindex(index=range(1, 13), columns=[2024, 2025])   # tolera años o meses sin datos
    )
    comp["dif_pct"] = (comp[2025] - comp[2024]) / comp[2024].where(comp[2024] != 0) * 100
    return comp


def fig_lineas(comp, medida):
    fig = go.Figure()
    for anio in [2024, 2025]:
        if comp[anio].notna().sum() == 0:
            continue
        fig.add_trace(go.Scatter(
            x=MESES, y=comp[anio], mode="lines+markers+text", name=str(anio),
            text=comp[anio], texttemplate="%{y:,.0f}", textposition="top center",
            line=dict(color=COLOR_ANIO[str(anio)]),
            hovertemplate="%{x} " + str(anio) + ": %{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(
        title=f"{medida.capitalize()} por mes: 2024 vs 2025",
        yaxis_title=medida.capitalize(), legend_title="Año",
        hovermode="x unified", height=450,
    )
    return fig


def fig_dif_mensual(comp, medida):
    colores = ["#2ca02c" if v >= 0 else "#d62728" for v in comp["dif_pct"].fillna(0)]
    fig = go.Figure(go.Bar(
        x=MESES, y=comp["dif_pct"], marker_color=colores,
        text=comp["dif_pct"], texttemplate="%{y:+.1f}%", textposition="outside",
        hovertemplate="%{x}: %{y:+.2f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_layout(
        title=f"Variación % de {medida} por mes: 2025 vs 2024",
        yaxis_title="Diferencia (%)", height=450,
    )
    return fig


def fig_total_anual(total, medida):
    dif = (total[2025] - total[2024]) / total[2024] * 100
    valores = [total[2024], total[2025]]
    ymax = max(valores)
    fig = go.Figure(go.Bar(
        x=["2024", "2025"], y=valores, marker_color=[COLOR_ANIO["2024"], COLOR_ANIO["2025"]],
        text=valores, texttemplate="%{y:,.0f}", textposition="outside",
        hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
    ))
    fig.add_annotation(
        x=0.5, y=ymax * 1.12, text=f"<b>{dif:+.1f}%</b>", showarrow=False,
        font=dict(size=22, color="#2ca02c" if dif >= 0 else "#d62728"),
    )
    fig.update_layout(
        title=f"{medida.capitalize()} total: 2024 vs 2025",
        yaxis=dict(range=[0, ymax * 1.25]), height=450,
    )
    return fig, dif


def veredicto(dif):
    if abs(dif - META_PCT) <= TOLERANCIA:
        st.success(f"Variación real: {dif:+.2f}%. La afirmación de +{META_PCT:.0f}% es aproximadamente correcta.")
    elif dif > META_PCT:
        st.warning(f"Variación real: {dif:+.2f}%. Se creció más de lo afirmado (+{META_PCT:.0f}%).")
    else:
        st.error(f"Variación real: {dif:+.2f}%. La afirmación de +{META_PCT:.0f}% no se sostiene con estos datos.")


def seccion(df, medida, clave):
    """Bloque completo de análisis para una medida (ventas o cantidad). Tolera datos incompletos."""
    if df.empty:
        st.info("No hay datos para esta selección.")
        return

    comp = comparativo_mensual(df, medida)
    total = df.groupby("anio")[medida].sum().reindex([2024, 2025])
    anios_con_datos = [a for a in [2024, 2025] if pd.notna(total[a])]

    # 1) Explicación mensual
    st.subheader(f"1. Breve explicación de {medida} por mes")
    if len(anios_con_datos) < 2:
        faltante = [a for a in [2024, 2025] if a not in anios_con_datos]
        st.info(f"No hay datos de {', '.join(map(str, faltante))}: se muestra solo lo disponible y no se puede comparar entre años.")
    st.plotly_chart(fig_lineas(comp, medida), use_container_width=True, key=f"{clave}_lineas")
    if comp["dif_pct"].notna().any():
        st.plotly_chart(fig_dif_mensual(comp, medida), use_container_width=True, key=f"{clave}_dif")
        meses_sin_comparar = comp["dif_pct"].isna().sum()
        if meses_sin_comparar:
            st.caption(f"{meses_sin_comparar} mes(es) sin dato en alguno de los dos años no tienen comparación.")
    tabla = comp.rename_axis("mes").reset_index()
    tabla["mes"] = tabla["mes"].map(lambda m: MESES[m - 1])
    st.dataframe(tabla.round(2), use_container_width=True, hide_index=True)

    # 2) Resumen anual
    st.subheader(f"2. Resumen anual de {medida}")
    if len(anios_con_datos) == 2 and total[2024] > 0:
        fig, dif = fig_total_anual(total, medida)
        c1, c2 = st.columns([2, 1])
        with c1:
            st.plotly_chart(fig, use_container_width=True, key=f"{clave}_total")
        with c2:
            st.metric("2024", f"{total[2024]:,.0f}")
            st.metric("2025", f"{total[2025]:,.0f}", f"{dif:+.2f}%")
            veredicto(dif)
    else:
        c1, c2 = st.columns(2)
        c1.metric("2024", "Sin datos" if pd.isna(total[2024]) else f"{total[2024]:,.0f}")
        c2.metric("2025", "Sin datos" if pd.isna(total[2025]) else f"{total[2025]:,.0f}")


def producto_top(df, df_suc, clave):
    """Producto más vendido en la sucursal (por cantidad y por ventas)."""
    if df_suc.empty or df_suc["producto"].dropna().empty:
        st.info("No hay información de productos para esta sucursal.")
        return

    prod = (
        df_suc.groupby("producto")
        .agg(cantidad=("cantidad", "sum"), ventas=("ventas", "sum"), registros=("producto", "size"))
        .reset_index()
    )
    ventas_suc = df_suc["ventas"].sum()
    ventas_global = df["ventas"].sum()
    prod["pct_ventas_sucursal"] = prod["ventas"] / ventas_suc * 100 if ventas_suc else float("nan")
    prod["pct_ventas_global"] = prod["ventas"] / ventas_global * 100 if ventas_global else float("nan")

    top_cant = prod.loc[prod["cantidad"].idxmax()]
    top_vent = prod.loc[prod["ventas"].idxmax()]

    c1, c2 = st.columns(2)
    for col, titulo, fila in [(c1, "Más vendido por cantidad", top_cant),
                              (c2, "Más vendido por valor de ventas", top_vent)]:
        with col:
            st.markdown(f"**{titulo}**")
            st.subheader(fila["producto"])
            m1, m2 = st.columns(2)
            m1.metric("Cantidad", f"{fila['cantidad']:,.0f}")
            m2.metric("Ventas", f"{fila['ventas']:,.0f}")
            m3, m4 = st.columns(2)
            m3.metric("% de ventas de la sucursal", pct_txt(fila["pct_ventas_sucursal"]))
            m4.metric("% de ventas globales", pct_txt(fila["pct_ventas_global"]))
    st.caption("% de ventas globales = ventas del producto en esta sucursal / ventas totales de todas las sucursales (2024-2025).")

    top10 = prod.sort_values("ventas", ascending=False).head(10).sort_values("ventas")
    fig = px.bar(top10, x="ventas", y="producto", orientation="h", text_auto=",.0f",
                 title="Top 10 productos por ventas en la sucursal")
    fig.update_layout(yaxis_title="", height=400)
    st.plotly_chart(fig, use_container_width=True, key=f"{clave}_top10")

    st.dataframe(
        prod.sort_values("ventas", ascending=False).round(2),
        use_container_width=True, hide_index=True,
    )


df = cargar()

st.title("¿En 2025 vendimos 4 % más que en 2024?")

tab_ventas, tab_cant, tab_reg, tab_suc = st.tabs(
    ["Global: ventas", "Global: cantidades", "Por región", "Por sucursal"]
)

with tab_ventas:
    seccion(df, "ventas", "global_ventas")

with tab_cant:
    st.caption("Aclaración: ¿el cambio en ventas viene de vender más unidades?")
    seccion(df, "cantidad", "global_cantidad")

with tab_reg:
    medida = st.radio("Medida", ["ventas", "cantidad"], horizontal=True)

    # Resumen comparativo de todas las regiones
    st.subheader(f"Comparativo de {medida} por región")
    reg = df.groupby(["region", "anio"])[medida].sum().unstack("anio")
    reg["dif_pct"] = (reg[2025] - reg[2024]) / reg[2024] * 100
    reg = reg.sort_values("dif_pct", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        reg_largo = (
            reg[[2024, 2025]].rename(columns=str).reset_index()
            .melt(id_vars="region", var_name="anio", value_name=medida)
        )
        fig = px.bar(
            reg_largo, x="region", y=medida, color="anio", barmode="group",
            color_discrete_map=COLOR_ANIO, text_auto=",.0f",
            title=f"{medida.capitalize()} anual por región",
        )
        fig.update_layout(legend_title="Año", xaxis_title="", height=450)
        st.plotly_chart(fig, use_container_width=True, key=f"reg_anual_{medida}")
    with c2:
        colores = ["#2ca02c" if v >= 0 else "#d62728" for v in reg["dif_pct"]]
        fig = go.Figure(go.Bar(
            x=reg.index, y=reg["dif_pct"], marker_color=colores,
            text=reg["dif_pct"], texttemplate="%{y:+.1f}%", textposition="outside",
            hovertemplate="%{x}: %{y:+.2f}%<extra></extra>",
        ))
        fig.add_hline(y=META_PCT, line_dash="dash", line_color="gray",
                      annotation_text=f"Meta +{META_PCT:.0f}%")
        fig.add_hline(y=0, line_color="black", line_width=1)
        fig.update_layout(title="Variación % 2025 vs 2024 por región",
                          yaxis_title="Diferencia (%)", height=450)
        st.plotly_chart(fig, use_container_width=True, key=f"reg_dif_{medida}")

    st.dataframe(reg.round(2).reset_index(), use_container_width=True, hide_index=True)

    # Mapa de calor: variación % por mes y región
    st.subheader("Variación % por mes y región")
    pivot = df.groupby(["region", "anio", "mes"])[medida].sum().unstack("anio")
    pivot["dif_pct"] = (pivot[2025] - pivot[2024]) / pivot[2024] * 100
    heat = pivot["dif_pct"].unstack("mes").reindex(columns=range(1, 13))
    heat.columns = MESES
    fig = px.imshow(
        heat, text_auto=".1f", aspect="auto",
        color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
        labels=dict(color="Diferencia (%)"),
    )
    fig.update_layout(xaxis_title="", yaxis_title="", height=300 + 40 * len(heat))
    st.plotly_chart(fig, use_container_width=True, key=f"reg_heat_{medida}")

    # Detalle de una región (mismo análisis que en las pestañas globales)
    st.subheader("Detalle por región")
    region_sel = st.selectbox("Región", sorted(df["region"].unique()))
    seccion(df[df["region"] == region_sel], medida, f"reg_{region_sel}_{medida}")

with tab_suc:
    sucursal_sel = st.selectbox("Sucursal", sorted(df["sucursal"].dropna().unique()), key="sel_sucursal")
    df_suc = df[df["sucursal"] == sucursal_sel]

    anios = sorted(df_suc["anio"].unique())
    regiones = ", ".join(map(str, df_suc["region"].dropna().unique())) or "n/d"
    st.caption(
        f"Región: {regiones} · {len(df_suc):,} registros · "
        f"años con datos: {', '.join(map(str, anios)) if anios else 'ninguno'}"
    )

    sub_v, sub_c, sub_p = st.tabs(["Ventas", "Cantidades", "Producto más vendido"])
    with sub_v:
        seccion(df_suc, "ventas", f"suc_{sucursal_sel}_ventas")
    with sub_c:
        seccion(df_suc, "cantidad", f"suc_{sucursal_sel}_cantidad")
    with sub_p:
        producto_top(df, df_suc, f"suc_{sucursal_sel}")
