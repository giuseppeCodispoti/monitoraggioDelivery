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
    orario_caricamento = orario_locale.strftime("%d-%m-%Y ore %H:%M")

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
        file_produzione = st.file_uploader("📂 Carica Produzione: data appuntamento oggi e stato pratica tutte", type=["xlsx", "xls"])

    with col_destra:
        if os.path.exists(logo_path):
            logo = Image.open(logo_path)
            st.image(logo, use_container_width=True)

    # ---------------------------------------
    # ELABORAZIONE
    # ---------------------------------------

    if file_produzione is not None:

        df = pd.read_excel(file_produzione)

        # -----------------------------------
        # ESCLUSIONE TIPOLOGIE LAVORO
        # -----------------------------------

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
            "VGW POTS+ADSL PERMUTA",
            "VGW POTS PERMUTA"
        ]

        df = df[
            ~df["Tipologia Lavoro"]
            .astype(str)
            .str.strip()
            .isin(tipologie_escluse)
        ]

        # -----------------------------------
        # ESCLUSIONE WR ANNULLATE
        # -----------------------------------

        df = df[
            df["Stato"]
            .astype(str)
            .str.strip()
            != "50 - Annullata"
        ]

        # -----------------------------------
        # ESCLUSIONE WR PER JOBTYPE
        # -----------------------------------

        jobtype_esclusi = [
            "ERCTZSDAC",
            "ERLHNI-V-H",
            "ERNHTZ--OP",
            "ERNHTZ--PP",
            "ERRARI-VGW",
            "ERRGRI-VGW",
            "ESDCATCL-R",
            "ETHVCDNC"
        ]

        df = df[
            ~df["JobType"]
            .astype(str)
            .str.strip()
            .isin(jobtype_esclusi)
        ]

        # -----------------------------------
        # ESCLUSIONE WR PER CODICE PROGETTO NAZIONALE
        # -----------------------------------

        progetto_nazionale_esclusi = [
            "MTW2622MLS",
            "TLC26E9I",
            "00BU62316K",
            "TLC26BRKXB",
            "MTW2608DES"
        ]

        df = df[
            ~df["Codice Progetto Nazionale"]
            .astype(str)
            .str.strip()
            .isin(progetto_nazionale_esclusi)
        ]

        df["Data Inizio Appuntamento"] = pd.to_datetime(
            df["Data Inizio Appuntamento"], errors="coerce"
        )

        data_riferimento = df["Data Inizio Appuntamento"].dt.date.max()

        df["Impresa"] = (
            df["Impresa"]
            .fillna("Sociale")
            .astype(str)
            .replace("nan", "Sociale")
        )

        # -----------------------------------
        # COSTRUZIONE AT
        # -----------------------------------

        df["distretto"] = df["Codice Centrale"].astype(str).str[:3]

        df["AT"] = df["distretto"].map({
            "964": "Bagnato",
            "965": "Votano",
            "966": "Bagnato"
        }).fillna("Carbone")

        # -----------------------------------
        # NORMALIZZAZIONE
        # -----------------------------------

        df["Impresa"] = df["Impresa"].astype(str)
        df["FTTH"] = df["FTTH"].astype(str).str.strip().str.upper()

        # -----------------------------------
        # PRODUTTIVE
        # -----------------------------------

        produttive = df[
            df["Causale Chiusura"]
            .astype(str)
            .str.strip()
            .eq("COMPLWR")
        ]

        # -----------------------------------
        # GIACENTI
        # -----------------------------------

        giacenti = (
            df.groupby(["AT", "Impresa"])
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
            df[df["FTTH"] == "TRUE"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Giacenti FTTH")
        )

        c_ftth = (
            produttive[produttive["FTTH"] == "TRUE"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Chiusi FTTH")
        )

        # -----------------------------------
        # NO FTTH
        # -----------------------------------

        g_no = (
            df[df["FTTH"] == "FALSE"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Giacenti NO FTTH")
        )

        c_no = (
            produttive[produttive["FTTH"] == "FALSE"]
            .groupby(["AT", "Impresa"])
            .size()
            .reset_index(name="Chiusi NO FTTH")
        )

        # -----------------------------------
        # IN LAVORAZIONE
        # -----------------------------------

        lavorazione = (
            df[
                (df["Stato"].astype(str).str.strip().eq("15 - In Lavorazione"))
                & (df["Data Inizio Appuntamento"].dt.date == data_riferimento)
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
            report["Produttivi"] / report["Giacenti"].replace(0, np.nan) * 100
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
                    "In Lavorazione": st.column_config.NumberColumn("In Lav.", width=60),
                }
            )

        with col_grafico:
            # Escludo la riga TOTALE
            dati_grafico = report[report["AT"] != "TOTALE"].copy()

            # Raggruppo SOLO per Impresa
            dati_grafico = (
                dati_grafico
                .groupby("Impresa", as_index=False)
                .agg({
                    "Giacenti": "sum",
                    "Produttivi": "sum"
                })
            )

            # Calcolo resa
            dati_grafico["Resa Totale %"] = (
                dati_grafico["Produttivi"]
                / dati_grafico["Giacenti"].replace(0, np.nan)
                * 100
            ).round(1)

            # Tolgo eventuali infiniti
            dati_grafico = dati_grafico.replace([np.inf, -np.inf], 0)

            # Ordino per resa
            dati_grafico = dati_grafico.sort_values(by="Resa Totale %", ascending=True)

            # Colori
            def colore_barra(val):
                if val >= 75:
                    return "#63BE7B"
                elif val >= 70.5:
                    return "#FFEB84"
                else:
                    return "#FFC7CE"

            dati_grafico["Colore"] = dati_grafico["Resa Totale %"].apply(colore_barra)

            fig = px.bar(
                dati_grafico,
                x="Resa Totale %",
                y="Impresa",
                orientation="h",
                title="Resa Totale % per Impresa",
                text="Resa Totale %"
            )

            fig.update_traces(
                marker_color=dati_grafico["Colore"],
                texttemplate="%{text:.1f}%",
                textposition="inside"
            )

            fig.update_layout(
                height=700,
                xaxis_title="",
                yaxis_title="",
                margin=dict(l=0, r=0, t=40, b=0)
            )

            st.plotly_chart(fig, use_container_width=True)

        # -----------------------------------
        # KO FTTH (FTTH = SI, Causale Chiusura ≠ COMPLWR)
        # -----------------------------------

        st.subheader("❌ Dettaglio KO FTTH")

        MACRO_CAUSALI = {"N43": "Non Reperibile",
                         "N44": "Rinuncia",
                         "C42": "Creation",
                         "C43": "Creation",
                         "C44": "Creation",
                         "C48": "Creation",
                         "A24": "Tubazione",
                         "A14": "Tubazione",
                         "N26": "Eccessiva Distanza",
                         "A10": "Indirizzo Errato",
                         "N52": "Centrale Errata",
                         "EQ1": "Centrale Errata",
                         "W50": "Opposizione",
                         "W55": "Oneroso",
                         "R87": "Rinuncia",
                         "W913": "Ricaduta",
                         "W914": "Ricaduta"}

        ko_ftth = df[
            (df["FTTH"] == "TRUE")
            & (df["Causale Chiusura"].notna())
            & (
                df["Causale Chiusura"]
                .astype(str)
                .str.strip()
                != ""
            )
            & (
                df["Causale Chiusura"]
                .astype(str)
                .str.strip()
                != "COMPLWR"
            )
        ].copy()

        if not ko_ftth.empty:

            ko_ftth["Causale Chiusura"] = (
                ko_ftth["Causale Chiusura"]
                .astype(str)
                .str.strip()
            )

            pivot_ko = pd.crosstab(
                ko_ftth["Impresa"],
                ko_ftth["Causale Chiusura"]
            )

            # Colonna Totale per risorsa
            pivot_ko["Totale"] = pivot_ko.sum(axis=1)

            # Ordino le risorse dal maggior numero di KO al minore
            pivot_ko = pivot_ko.sort_values(by="Totale", ascending=False)

            # Riga Totale per causale, in fondo
            pivot_ko.loc["TOTALE"] = pivot_ko.sum(axis=0)

            pivot_ko = pivot_ko.reset_index().rename(columns={"Impresa": "Risorsa"})

            colonne_causali = [
                c for c in pivot_ko.columns if c not in ("Risorsa", "Totale")
            ]

            def colora_ko(val):
                try:
                    val = float(val)
                    if val <= 0:
                        return ""
                    elif val == 1:
                        return "background-color:#FFC7CE"
                    elif val == 2:
                        return "background-color:#FF8A80"
                    elif val == 3:
                        return "background-color:#FF5252;color:white"
                    else:
                        return "background-color:#B71C1C;color:white"
                except Exception:
                    return ""

            st.dataframe(
                pivot_ko.style
                .hide(axis="index")
                .format({col: "{:.0f}" for col in colonne_causali + ["Totale"]})
                .set_properties(**{"font-weight": "bold"}, subset=["Risorsa", "Totale"])
                .map(
                    colora_ko,
                    subset=colonne_causali
                ),
                use_container_width=True,
                height=(len(pivot_ko) + 1) * 35 + 3
            )

        else:
            st.info("Nessun KO FTTH presente nei dati caricati.")

        # -----------------------------------
        # EXCEL
        # -----------------------------------

        output = BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            report.to_excel(writer, index=False, sheet_name="Resa")
            if not ko_ftth.empty:
                pivot_ko.to_excel(writer, index=False, sheet_name="KO FTTH")

        output.seek(0)

        st.download_button(
            label="📥 Scarica Excel",
            data=output,
            file_name="resa_giornaliera.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
