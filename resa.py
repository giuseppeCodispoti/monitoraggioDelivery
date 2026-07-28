import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
from io import BytesIO
from PIL import Image
from datetime import datetime
import pytz
import os

def run():
    st.set_page_config(
        page_title="Resa del Giorno",
        layout="wide"
    )
    
    # ---------------------------------------
    # DATA E ORA
    # ---------------------------------------
    
    rome_tz = pytz.timezone("Europe/Rome")
    
    orario_locale = datetime.now(rome_tz)
    
    orario_caricamento = orario_locale.strftime(
        "%d-%m-%Y ore %H:%M"
    )
    
    # ---------------------------------------
    # LOGO
    # ---------------------------------------
    # NB: il percorso originale era fisso sul PC dell'utente (C:\Users\g.codispoti\...).
    # Se l'app gira su un altro computer o su un server (es. Streamlit Cloud),
    # quel file non esiste e l'app va in crash all'avvio.
    # Soluzione: cerco un logo.png nella stessa cartella dello script; se non c'è,
    # semplicemente non mostro il logo invece di bloccare l'app.
    
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    
    # ---------------------------------------
    # TITOLO (centrato, in cima)
    # ---------------------------------------
    
    st.markdown(
        f"""
        <h4 style='text-align:center;'>
        📈 Resa del Giorno 📈
        <br>
        <strong>{orario_caricamento}</strong>
        </h4>
        """,
        unsafe_allow_html=True
    )
    
    # ---------------------------------------
    # UPLOAD (sinistra) + FOTO/LOGO (destra), affiancati
    # ---------------------------------------
    
    col_sinistra, col_destra = st.columns([4, 1])
    
    with col_sinistra:
        file_giacenza = st.file_uploader(
            "📂 Carica Giacenza",
            type=["xlsx", "xls"]
        )
    
        file_chiusura = st.file_uploader(
            "📂 Carica Chiusura",
            type=["xlsx", "xls"]
        )
    
    with col_destra:
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            st.image(logo, use_container_width=True)
    
    # ---------------------------------------
    # ELABORAZIONE
    # ---------------------------------------
    
    if file_giacenza is not None and file_chiusura is not None:
    
        df_g = pd.read_excel(file_giacenza)
        df_c = pd.read_excel(file_chiusura)
    
        df_g["Impresa"] = (
            df_g["Impresa"]
            .fillna("Sociale")
            .astype(str)
            .replace("nan", "Sociale")
        )
        df_c["Impresa"] = (
            df_c["Impresa"]
            .fillna("Sociale")
            .astype(str)
            .replace("nan", "Sociale")
        )
    
        # -----------------------------------
        # COSTRUZIONE AT
        # -----------------------------------
    
        df_g["distretto"] = (
            df_g["Codice Centrale"]
            .astype(str)
            .str[:3]
        )
    
        df_g["AT"] = df_g["distretto"].map({
            "964": "Bagnato",
            "965": "Votano",
            "966": "Bagnato"
        }).fillna("Carbone")
    
        df_c["distretto"] = (
            df_c["Codice Centrale"]
            .astype(str)
            .str[:3]
        )
    
        df_c["AT"] = df_c["distretto"].map({
            "964": "Bagnato",
            "965": "Votano",
            "966": "Bagnato"
        }).fillna("Carbone")
    
        # -----------------------------------
        # NORMALIZZAZIONE
        # -----------------------------------
    
        df_g["Impresa"] = df_g["Impresa"].astype(str)
        df_c["Impresa"] = df_c["Impresa"].astype(str)
    
        df_g["FTTH"] = df_g["FTTH"].astype(str)
        df_c["FTTH"] = df_c["FTTH"].astype(str)
    
        # -----------------------------------
        # PRODUTTIVE
        # -----------------------------------
    
        produttive = df_c[
            df_c["Causale Chiusura"]
            .astype(str)
            .str.strip()
            .eq("COMPLWR")
        ]
    
        # -----------------------------------
        # GIACENTI
        # -----------------------------------
    
        giacenti = (
            df_g.groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Giacenti")
        )
    
        # -----------------------------------
        # CHIUSI PRODUTTIVI
        # -----------------------------------
    
        chiusi = (
            produttive.groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Produttivi")
        )
    
        # -----------------------------------
        # FTTH
        # -----------------------------------
    
        g_ftth = (
            df_g[df_g["FTTH"] == "True"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Giacenti FTTH")
        )
    
        c_ftth = (
            produttive[produttive["FTTH"] == "True"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Chiusi FTTH")
        )
    
        # -----------------------------------
        # NO FTTH
        # -----------------------------------
    
        g_no = (
            df_g[df_g["FTTH"] == "False"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Giacenti NO FTTH")
        )
    
        c_no = (
            produttive[produttive["FTTH"] == "False"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Chiusi NO FTTH")
        )
    
        # -----------------------------------
        # IN LAVORAZIONE
        # -----------------------------------
    
        lavorazione = (
            df_g[
                df_g["Stato"]
                .astype(str)
                .str.strip()
                .eq("15 - In Lavorazione")
            ]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="In Lavorazione")
        )
    
        # -----------------------------------
        # MERGE
        # -----------------------------------
    
        report = giacenti.merge(chiusi, on=["AT", "Impresa"], how="left")
        report = report.merge(g_ftth, on=["AT", "Impresa"], how="left")
        report = report.merge(c_ftth, on=["AT", "Impresa"], how="left")
        report = report.merge(g_no, on=["AT", "Impresa"], how="left")
        report = report.merge(c_no, on=["AT", "Impresa"], how="left")
        report = report.merge(lavorazione, on=["AT", "Impresa"], how="left")
    
        report = report.fillna(0)
    
        # -----------------------------------
        # RESE
        # -----------------------------------
    
        report["Resa Totale %"] = (
            report["Produttivi"] / report["Giacenti"] * 100
        ).round(1)
    
        report["Resa FTTH %"] = (
            report["Chiusi FTTH"] / report["Giacenti FTTH"].replace(0, np.nan) * 100
        ).round(1)
    
        report["Resa NO FTTH %"] = (
            report["Chiusi NO FTTH"] / report["Giacenti NO FTTH"].replace(0, np.nan) * 100
        ).round(1)
    
        report = report.fillna(0)
    
        # -----------------------------------
        # ORDINAMENTO
        # -----------------------------------
    
        report = report[
            [
                "AT",
                "Impresa",
                "Giacenti",
                "Produttivi",
                "Resa Totale %",
                "Resa FTTH %",
                "Resa NO FTTH %",
                "In Lavorazione"
            ]
        ]
    
        report = report.sort_values(by=["AT", "Impresa"]).reset_index(drop=True)
    
        # -----------------------------------
        # TOTALE FINALE
        # -----------------------------------
    
        tot_ftth = (
            round(c_ftth["Chiusi FTTH"].sum() / g_ftth["Giacenti FTTH"].sum() * 100, 1)
            if not g_ftth.empty and g_ftth["Giacenti FTTH"].sum() > 0
            else 0
        )
    
        tot_no_ftth = (
            round(c_no["Chiusi NO FTTH"].sum() / g_no["Giacenti NO FTTH"].sum() * 100, 1)
            if not g_no.empty and g_no["Giacenti NO FTTH"].sum() > 0
            else 0
        )
    
        totale = pd.DataFrame(
            [{
                "AT": "TOTALE",
                "Impresa": "",
                "Giacenti": report["Giacenti"].sum(),
                "Produttivi": report["Produttivi"].sum(),
                "Resa Totale %": (
                    round(report["Produttivi"].sum() / report["Giacenti"].sum() * 100, 1)
                    if report["Giacenti"].sum() > 0 else 0
                ),
                "Resa FTTH %": tot_ftth,
                "Resa NO FTTH %": tot_no_ftth,
                "In Lavorazione": report["In Lavorazione"].sum()
            }]
        )
    
        report = pd.concat([report, totale], ignore_index=True)
    
        # Nasconde le ripetizioni della colonna "AT" per le righe con lo stesso distretto
        # (solo estetico, la riga TOTALE resta sempre visibile)
        mask_totale = report["AT"] == "TOTALE"
    
        report.loc[~mask_totale, "AT"] = (
            report.loc[~mask_totale, "AT"]
            .mask(report.loc[~mask_totale, "AT"].duplicated(), "")
        )
    
        # -----------------------------------
        # KPI
        # -----------------------------------
    
        # NB: escludo la riga "TOTALE" dalla somma, perché è già essa stessa
        # la somma delle righe sopra: sommarla di nuovo raddoppierebbe i valori
        # (bug segnalato: KPI e Resa % risultavano il doppio del reale).
        totale_giacenti = report.loc[~mask_totale, "Giacenti"].sum()
        totale_produttive = report.loc[~mask_totale, "Produttivi"].sum()
        totale_lavorazione = report.loc[~mask_totale, "In Lavorazione"].sum()
    
        resa_generale = (
            round(totale_produttive / totale_giacenti * 100, 1)
            if totale_giacenti > 0 else 0
        )
    
        c1, c2, c3, c4 = st.columns(4)
    
        c1.metric("Giacenti", int(totale_giacenti))
        c2.metric("Produttive", int(totale_produttive))
        c3.metric("In Lav.", int(totale_lavorazione))
        c4.metric("Resa %", f"{resa_generale}%")
    
        # -----------------------------------
        # COLORAZIONI
        # -----------------------------------
    
        def colora_resa(val):
            try:
                val = float(val)
                if val >= 75:
                    return "background-color:#C6EFCE"
                elif val >= 70:
                    return "background-color:#FFEB9C"
                else:
                    return "background-color:#FFC7CE"
            except Exception:
                return ""
    
        st.subheader("📈 Resa per Risorsa")
    
        report["Impresa"] = report["Impresa"].astype(str)
    
        st.markdown(
            """<style>
            [data-testid="stDataFrame"] {
            font-size: 12px;}
            </style>
            """,
            unsafe_allow_html=True
        )
    
        # -----------------------------------
        # TABELLA + GRAFICO ISTOGRAMMA AFFIANCATI
        # -----------------------------------
    
        col_tabella, col_grafico = st.columns([2, 1])
    
        with col_tabella:
            st.dataframe(
                report.style
                .hide(axis="index")
                .format({
                    "Produttivi": "{:.0f}",
                    "In Lavorazione": "{:.0f}",
                    "Resa Totale %": "{:.1f}",
                    "Resa FTTH %": lambda x: "" if pd.isna(x) else f"{x:.1f}",
                    "Giacenti": "{:.0f}",
                    "Resa NO FTTH %": lambda x: "" if pd.isna(x) else f"{x:.1f}",
                })
                .set_properties(**{"font-weight": "bold"})
                .map(
                    colora_resa,
                    subset=["Resa Totale %", "Resa FTTH %", "Resa NO FTTH %"]
                ),
                use_container_width=False,
                height=(len(report) + 1) * 35 + 3,
                column_config={
                    "AT": st.column_config.TextColumn(width="small"),
                    "Impresa": st.column_config.TextColumn(width="medium"),
                    "Giacenti": st.column_config.NumberColumn(width="small"),
                    "Produttivi": st.column_config.NumberColumn(width="small"),
                    "Resa Totale %": st.column_config.NumberColumn("ResaTot. %", width=75),
                    "Resa FTTH %": st.column_config.NumberColumn("RESA FTTH %", width=90),
                    "Resa NO FTTH %": st.column_config.NumberColumn("RESA≠FTTH %", width=90),
                    "In Lavorazione":  st.column_config.NumberColumn("In Lav.", width=60),
                }
            )
    
        #with col_grafico:
            # Escludo la riga TOTALE dal grafico (altrimenti falsa la scala delle barre)
            #dati_grafico = report[report["AT"] != "TOTALE"].copy()
            #dati_grafico = dati_grafico[dati_grafico["Impresa"] != ""]
    
           # def colore_barra(val):
                #if val >= 75:
                    #return "#63BE7B"   # verde
                #elif val >= 70:
                    #return "#FFEB84"   # giallo
               # else:
                   # return "#FFC7CE"   # rosso
    
           # dati_grafico["Colore"] = dati_grafico["Resa Totale %"].apply(colore_barra)
    
           # fig = px.bar(
                #dati_grafico,
                #x="Resa Totale %",
                #y="Impresa",
                #orientation="h",
                #title="Resa Totale % per Impresa",
                #text="Resa Totale %"
            #)
            #fig.update_traces(
                #marker_color=dati_grafico["Colore"],
               # texttemplate="%{text:.1f}%",
                #textposition="inside",
               # textfont=dict(color="black", size=12)
           # )
            #fig.update_layout(
               # height=(len(report) + 1) * 35 + 3,
                #xaxis_title="",
                #yaxis_title="",
                #margin=dict(l=0, r=0, t=40, b=0),
               # plot_bgcolor="white",
                #xaxis=dict(
                 #   showgrid=True,
                  #  gridcolor="#D9D9D9",
                  #  gridwidth=1,
                   # showline=True,
                  #  linecolor="#B0B0B0"
               # ),
               # yaxis=dict(
                  #  showgrid=True,
                   # gridcolor="#D9D9D9",
                   # gridwidth=1,
                   # showline=True,
                   # linecolor="#B0B0B0"
              #  )
          #  )
    
          #  st.plotly_chart(fig, use_container_width=True)
    
        # -----------------------------------
        # EXCEL
        # -----------------------------------
    
        output = BytesIO()
    
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            report.to_excel(writer, index=False, sheet_name="Resa")
    
        output.seek(0)
    
        st.download_button(
            label="📥 Scarica Excel",
            data=output,
            file_name="resa_giornaliera.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
