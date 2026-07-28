import streamlit as st

scelta = st.selectbox(
    "📊 Scegli l'app da eseguire 📊 ",
    [
        "programmazione ",
        "resa"
    ]
)

if scelta == "programmazioneD":
    import programmazione
    programmazione.run()

elif scelta == "resa":
    import resa
    resa.run()

