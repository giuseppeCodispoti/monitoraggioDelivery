import pandas as pd
import plotly.express as px
import streamlit as st
import sys
from io import BytesIO
from PIL import Image
from datetime import datetime
import pytz
import os

def run():

    st.set_page_config(
        page_title="Programmazione delivery",
        layout="centered"
    )
    
    # Data e ora
    
    rome_tz = pytz.timezone("Europe/Rome")
    
    orario_locale = datetime.now(rome_tz)
    
    orario_caricamento = orario_locale.strftime(
        "%d-%m-%Y ore %H:%M"
    )
    
    # Logo
    
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    
    logo = Image.open(logo_path)
    col1, col2, col3 = st.columns([3, 3, 3])
    
    with col2:
        st.image(logo, width=500)
    
    st.markdown(
        f"""
        <h4 style='text-align:center;'>
        🎯 Giacenza delivery 🎯
        <br>
        <strong>{orario_caricamento}</strong>
        </h4>
        """,
        unsafe_allow_html=True
    )
    
    # Upload file
    
    file_giacenza = st.file_uploader(
        "Carica il file Excel di giacenza",
        type=["xlsx", "xls"]
    )
    
    # Elaborazione
    
    if file_giacenza is not None:
    
        df = pd.read_excel(file_giacenza)
        tipologie_escluse = [
            "PREDISPOSIZIONE BRETELLE OTTICHE",
            "FTTC LA: PERMUTA+LA+COLLAUDO+OUTSOURCING",
            "FTTC LA: PERMUTA+LA+COLLAUDO",
            "FTTH: SOSTITUZIONE ONT",
            "CDN HV-COL",
            "FTTC LA: PERMUTA+LA+INST PRODOT",
            "INSTALLAZIONE APPARATI CATALYST",
            "FTTC LA: PERMUTA+LA+INST PRODOT+OUTSOURCING",
            "FTTC-FTTE TZ:PERM SECONDARIA A DAC S INT",
            "FTTC-FTTE TZ:PERM SECONDARIA A DAC S INT",
            "VGW POTS+ADSL PERMUTA",
            "VGW POTS PERMUTA"]

        df= df[~df["Tipologia Lavoro"]
                    .astype(str)
                    .str.strip()
                    .isin(tipologie_escluse)
        ]

        # Esclusione WR Annullate

        df = df[
            df["Stato"]
            .astype(str)
            .str.strip()
            != "50 - Annullata"
        ]

        # Esclusione WR per JobType

        jobtype_esclusi = [
            "ERCTZSDAC",
            "ERLHNI-V-H",
            "ERNHTZ--OP",
            "ERNHTZ--PP",
            "ERRARI-VGW",
            "ERRGRI-VGW",
            "ESDCATCL-R",
            "MTW2622MLS",
            "TLC26E9I",
            "00BU62316K",
            "TLC26BRKXB",
            "MTW2608DES",
            "ETHVCDNC"]

        df = df[
            ~df["JobType"]
            .astype(str)
            .str.strip()
            .isin(jobtype_esclusi)
        ]

        # Esclusione WR per Codice Progetto Nazionale

        progetto_nazionale_esclusi = [
            "MTW2622MLS",
            "MTW2608DES"]

        df = df[
            ~df["Codice Progetto Nazionale"]
            .astype(str)
            .str.strip()
            .isin(progetto_nazionale_esclusi)
        ]

    
        # Distretto
    
        df["distretto"] = (
            df["Codice Centrale"]
            .astype(str)
            .str[:3]
        )
    
        df["at"] = df["distretto"].map({
            "964": "Bagnato",
            "965": "Votano",
            "966":"Varamo",
            "966": "Bagnato"
        }).fillna("Carbone")
    
        # Impresa
    
        df["Impresa"] = (
            df["Impresa"]
            .fillna("Sociale")
        )
    
        # FTTH True/False
    
        df["FTTH"] = (
            df["FTTH"]
            .astype(str)
            .str.upper()
        )
    
        # Giacenza Totale
    
        pivot_totale = (
            df.groupby(
                ["at", "Impresa"]
            )
            .size()
            .reset_index(
                name="Giacenza Totale"
            )
        )
    
        # OL FTTH
    
        pivot_ftth = (
            df[
                df["FTTH"].isin(
                    ["TRUE", "SI", "1"]
                )
            ]
            .groupby(
                ["at", "Impresa"]
            )
            .size()
            .reset_index(
                name="OL FTTH"
            )
        )
    
        # OL NO FTTH
    
        pivot_no_ftth = (
            df[
                ~df["FTTH"].isin(
                    ["TRUE", "SI", "1"]
                )
            ]
            .groupby(
                ["at", "Impresa"]
            )
            .size()
            .reset_index(
                name="OL NO FTTH"
            )
        )
    
        # Merge
    
        pivot = pivot_totale.merge(
            pivot_ftth,
            on=["at", "Impresa"],
            how="left"
        )
    
        pivot = pivot.merge(
            pivot_no_ftth,
            on=["at", "Impresa"],
            how="left"
        )
    
        pivot = pivot.fillna(0)
    
        # Ordinamento
    
        pivot_sorted = (
            pivot
            .sort_values(
                by=["at", "Impresa"]
            )
            .reset_index(drop=True)
        )
    
        # Mostra AT una sola volta
    
        pivot_sorted["at"] = (
            pivot_sorted.groupby("at")["at"]
            .transform(
                lambda x: x.mask(
                    x.index != x.index[0],
                    ""
                )
            )
        )
    
        # Totale finale
    
        totale = pd.DataFrame(
            [[
                "Totale complessivo",
                "",
    
                pivot["Giacenza Totale"].sum(),
    
                pivot["OL FTTH"].sum(),
    
                pivot["OL NO FTTH"].sum()
            ]],
            columns=[
                "at",
                "Impresa",
                "Giacenza Totale",
                "OL FTTH",
                "OL NO FTTH"
            ]
        )
    
        pivot_formattata = pd.concat(
            [pivot_sorted, totale],
            ignore_index=True
        )
    
        # Tabella
    
    
        st.dataframe(
            pivot_formattata,
            use_container_width=True
        )
    
        # Export Excel
    
        output = BytesIO()
    
        with pd.ExcelWriter(
            output,
            engine="xlsxwriter"
        ) as writer:
    
            pivot_formattata.to_excel(
                writer,
                index=False,
                sheet_name="Programmazione"
            )
    
        output.seek(0)
    
        st.download_button(
            label="📥 Scarica programmazione",
            data=output,
            file_name="programmazione.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Export Excel dettaglio WR

        output_dettaglio = BytesIO()

        with pd.ExcelWriter(
            output_dettaglio,
            engine="xlsxwriter"
        ) as writer:

            df.to_excel(
                writer,
                index=False,
                sheet_name="Dettaglio WR"
            )

        output_dettaglio.seek(0)

        st.download_button(
            label="📥 Scarica dettaglio WR",
            data=output_dettaglio,
            file_name="dettaglio_wr.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
        # Grafico a torta
    
        st.subheader(
            " 📦 Distribuzione Giacenza per Impresa 📦"
        )
    
        df_pie = pivot_sorted.dropna(subset=["Impresa", "Giacenza Totale"])
        fig = px.pie(df_pie,
                 names="Impresa",
                 values="Giacenza Totale",
                 title="Distribuzione Giacenza per Impresa")
        st.plotly_chart(fig)
    
 
