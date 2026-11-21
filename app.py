import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

st.set_page_config(page_title="Ventas 2024 vs 2025", layout="wide")

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
META_PCT = 4.0      # afirmación a verificar
TOLERANCIA = 0.5    # puntos porcentuales para considerarla "aproximadamente correcta"


@st.cache_data
def cargar():
    df = pd.read_csv("ventas_mensuales.csv")
    return df[df["anio"].isin([2024, 2025])]


def comparativo_mensual(df, medida):
    comp = (
        df.groupby(["anio", "mes"])[medida].sum().reset_index()
        .pivot(index="mes", columns="anio", values=medida)
        .reindex(range(1, 13))
    )
    comp["dif_pct"] = (comp[2025] - comp[2024]) / comp[2024] * 100
    return comp


def fig_lineas(comp, medida):
    fig, ax = plt.subplots(figsize=(13, 5))
    for anio in [2024, 2025]:
        ax.plot(comp.index, comp[anio], marker="o", label=str(anio))
        for x, y in zip(comp.index, comp[anio]):
            if pd.notna(y):
                ax.annotate(f"{y:,.0f}", (x, y), textcoords="offset points",
                            xytext=(0, 8), ha="center", fontsize=8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MESES)
    ax.set_title(f"{medida.capitalize()} por mes: 2024 vs 2025")
    ax.set_ylabel(medida.capitalize())
    ax.legend(title="Año")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def fig_dif_mensual(comp, medida):
    fig, ax = plt.subplots(figsize=(13, 5))
    colores = comp["dif_pct"].apply(lambda v: "tab:green" if v >= 0 else "tab:red")
    barras = ax.bar(comp.index, comp["dif_pct"], color=colores)
    for b, v in zip(barras, comp["dif_pct"]):
        if pd.notna(v):
            ax.annotate(f"{v:+.1f}%", (b.get_x() + b.get_width() / 2, v),
                        textcoords="offset points", xytext=(0, 5 if v >= 0 else -12),
                        ha="center", fontsize=9)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MESES)
    ax.set_title(f"Variación % de {medida} por mes: 2025 vs 2024")
    ax.set_ylabel("Diferencia (%)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def fig_total_anual(total, medida):
    dif = (total[2025] - total[2024]) / total[2024] * 100
    fig, ax = plt.subplots(figsize=(7, 5))
    barras = ax.bar(["2024", "2025"], [total[2024], total[2025]], color=["tab:blue", "tab:orange"])
    for b, v in zip(barras, [total[2024], total[2025]]):
        ax.annotate(f"{v:,.0f}", (b.get_x() + b.get_width() / 2, v),
                    textcoords="offset points", xytext=(0, 5), ha="center", fontsize=10)
    ymax = max(total[2024], total[2025])
    ax.annotate(f"{dif:+.1f}%", xy=(0.5, ymax * 1.08), ha="center", fontsize=14,
                fontweight="bold", color="tab:green" if dif >= 0 else "tab:red")
    ax.set_ylim(0, ymax * 1.18)
    ax.set_title(f"{medida.capitalize()} total: 2024 vs 2025")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig, dif


def veredicto(dif):
    if abs(dif - META_PCT) <= TOLERANCIA:
        st.success(f"Variación real: {dif:+.2f}%. La afirmación de +{META_PCT:.0f}% es aproximadamente correcta.")
    elif dif > META_PCT:
        st.warning(f"Variación real: {dif:+.2f}%. Se creció más de lo afirmado (+{META_PCT:.0f}%).")
    else:
        st.error(f"Variación real: {dif:+.2f}%. La afirmación de +{META_PCT:.0f}% no se sostiene con estos datos.")


def seccion(df, medida, clave):
    """Bloque completo de análisis para una medida (ventas o cantidad)."""
    comp = comparativo_mensual(df, medida)
    total = df.groupby("anio")[medida].sum()

    # 1) Explicación mensual
    st.subheader(f"1. Breve explicación de {medida} por mes")
    st.pyplot(fig_lineas(comp, medida))
    st.pyplot(fig_dif_mensual(comp, medida))
    tabla = comp.rename_axis("mes").reset_index()
    tabla["mes"] = tabla["mes"].map(lambda m: MESES[m - 1])
    st.dataframe(tabla.round(2), use_container_width=True, hide_index=True)

    # 2) Resumen anual
    st.subheader(f"2. Resumen anual de {medida}")
    fig, dif = fig_total_anual(total, medida)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.pyplot(fig)
    with c2:
        st.metric("2024", f"{total[2024]:,.0f}")
        st.metric("2025", f"{total[2025]:,.0f}", f"{dif:+.2f}%")
        veredicto(dif)


df = cargar()

st.title("¿En 2025 vendimos 4 % más que en 2024?")

tab_ventas, tab_cant, tab_reg = st.tabs(["Global: ventas", "Global: cantidades", "Por región"])

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
        fig, ax = plt.subplots(figsize=(8, 5))
        x = range(len(reg))
        ax.bar([i - 0.2 for i in x], reg[2024], width=0.4, label="2024", color="tab:blue")
        ax.bar([i + 0.2 for i in x], reg[2025], width=0.4, label="2025", color="tab:orange")
        ax.set_xticks(list(x))
        ax.set_xticklabels(reg.index, rotation=45)
        ax.set_title(f"{medida.capitalize()} anual por región")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        st.pyplot(fig)
    with c2:
        fig, ax = plt.subplots(figsize=(8, 5))
        colores = reg["dif_pct"].apply(lambda v: "tab:green" if v >= 0 else "tab:red")
        barras = ax.bar(reg.index, reg["dif_pct"], color=colores)
        for b, v in zip(barras, reg["dif_pct"]):
            ax.annotate(f"{v:+.1f}%", (b.get_x() + b.get_width() / 2, v),
                        textcoords="offset points", xytext=(0, 5 if v >= 0 else -12),
                        ha="center", fontsize=9)
        ax.axhline(META_PCT, color="gray", linestyle="--", label=f"Meta +{META_PCT:.0f}%")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title("Variación % 2025 vs 2024 por región")
        ax.tick_params(axis="x", rotation=45)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        st.pyplot(fig)

    st.dataframe(reg.round(2).reset_index(), use_container_width=True, hide_index=True)

    # Mapa de calor: variación % por mes y región
    st.subheader("Variación % por mes y región")
    pivot = (
        df.groupby(["region", "anio", "mes"])[medida].sum().unstack("anio")
    )
    pivot["dif_pct"] = (pivot[2025] - pivot[2024]) / pivot[2024] * 100
    heat = pivot["dif_pct"].unstack("mes").reindex(columns=range(1, 13))
    heat.columns = MESES
    fig, ax = plt.subplots(figsize=(13, 4 + 0.4 * len(heat)))
    sns.heatmap(heat, annot=True, fmt=".1f", cmap="RdYlGn", center=0, ax=ax,
                cbar_kws={"label": "Diferencia (%)"})
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    st.pyplot(fig)

    # Detalle de una región (mismo análisis que en las pestañas globales)
    st.subheader("Detalle por región")
    region_sel = st.selectbox("Región", sorted(df["region"].unique()))
    seccion(df[df["region"] == region_sel], medida, f"reg_{region_sel}_{medida}")
