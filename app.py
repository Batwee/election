import unicodedata
import pandas as pd
import requests
import streamlit as st

# Import direct du dictionnaire (ou collez le dictionnaire au début de app.py)
from themes import THEMES

st.set_page_config(page_title="Votes Assemblée Nationale", page_icon="🏛️", layout="wide")

URL_API = "https://raw.githubusercontent.com/Batwee/updatevotes/main/votes.json"

def normalize(text: str) -> str:
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()

@st.cache_data(ttl=3600)
def load_votes():
    try:
        res = requests.get(URL_API)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return []

scrutins = load_votes()

if not scrutins:
    st.warning("Aucune donnée disponible.")
    st.stop()

# --------------------------------------------------------------------------- #
# Menu & Filtres
# --------------------------------------------------------------------------- #

st.title("🏛️ Votes de l'Assemblée nationale")

with st.sidebar:
    st.header("Filtres")
    
    # Sélecteur de thèmes avec option "Tous"
    options_themes = ["Tous les thèmes"] + list(THEMES.keys())
    theme_choisi = st.selectbox("Filtrer par thème :", options=options_themes)
    
    only_final = st.checkbox("Uniquement les votes d'ensemble", value=True)

# --------------------------------------------------------------------------- #
# Logic de filtrage
# --------------------------------------------------------------------------- #

filtered_scrutins = []

for s in scrutins:
    titre_norm = normalize(s.get("titre", ""))
    
    # 1. Filtre sur "Vote d'ensemble"
    if only_final and "ensemble" not in titre_norm:
        continue
    
    # 2. Filtre par Thème
    if theme_choisi != "Tous les thèmes":
        keywords = THEMES.get(theme_choisi, [])
        # On vérifie si au moins un mot-clé du thème est présent dans le titre
        match = any(normalize(kw) in titre_norm for kw in keywords)
        if not match:
            continue
            
    filtered_scrutins.append(s)

if not filtered_scrutins:
    st.warning("Aucun scrutin ne correspond au thème sélectionné.")
    st.stop()

# --------------------------------------------------------------------------- #
# Sélecteur du Scrutin
# --------------------------------------------------------------------------- #

def format_titre(s) -> str:
    t = s.get("titre", "Scrutin sans titre")
    return t[:120] + "..." if len(t) > 120 else t

st.write(f"**{len(filtered_scrutins)}** scrutin(s) trouvé(s)")

index_choisi = st.selectbox(
    "Sélectionnez un projet / proposition de loi :",
    options=range(len(filtered_scrutins)),
    format_func=lambda i: format_titre(filtered_scrutins[i])
)

vote = filtered_scrutins[index_choisi]

# --------------------------------------------------------------------------- #
# Affichage du Scrutin Sélectionné
# --------------------------------------------------------------------------- #

st.divider()
st.subheader(vote.get("titre"))

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.write(f"**Scrutin n° :** {vote.get('numero')}")
col_m2.write(f"**Date du vote :** {vote.get('date')}")

sort_info = str(vote.get("sort", "Non précisé"))
if "adopté" in sort_info.lower():
    col_m3.success(f"**Résultat :** {sort_info}")
else:
    col_m3.error(f"**Résultat :** {sort_info}")

if vote.get("demandeur"):
    st.caption(f"**Demandeur :** {vote.get('demandeur')}")

# --- SYNTHÈSE GLOBALE ---
st.markdown("### 📊 Synthèse globale du vote")
syn = vote.get("syntheseVote", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pour 🟩", syn.get("pour", 0))
c2.metric("Contre 🟥", syn.get("contre", 0))
c3.metric("Abstentions 🟧", syn.get("abstention", 0))
c4.metric("Total Votants 👥", syn.get("total", 0))

# --- GRAPHIQUE PAR GROUPE ---
st.divider()
st.markdown("### 🏛️ Répartition des votes par groupe politique")

groupes = vote.get("groupes", [])

if not groupes:
    st.info("Le détail par groupe politique n'est pas disponible pour ce scrutin.")
else:
    df = pd.DataFrame(groupes)
    
    if "sigle" in df.columns:
        df = df.set_index("sigle")[["pour", "contre", "abstention"]]
        df["total"] = df["pour"] + df["contre"] + df["abstention"]
        df = df[df["total"] > 0].drop(columns=["total"])

        if not df.empty:
            st.bar_chart(
                df,
                color=["#2ecc71", "#e74c3c", "#f39c12"],
                height=400
            )
        else:
            st.info("Aucun vote enregistré dans les groupes pour ce scrutin.")
