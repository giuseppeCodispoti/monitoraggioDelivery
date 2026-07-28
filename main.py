import streamlit as st

scelta = st.selectbox("Scegli l'app da eseguire:", ["programmazione", "resa"])
if scelta == "programmazione":
    import programmazioneD
    programmazioneD.run()
elif scelta == "resa":
    import resa
    resa.run()

