import unicodedata
import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Votes Assemblée Nationale",
    page_icon="🏛️",
    layout="wide"
)

URL_API = "https://cdn.jsdelivr.net/gh/Batwee/updatevotes@main/votes.json"

def normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower()

@st.cache_data(ttl=3600)
def load_votes():
    try:
        response = requests.get(URL_API)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"Impossible de récupérer la liste des scrutins : {e}")
        return []

scrutins = load_votes()

if not scrutins:
    st.warning("Aucune donnée disponible pour le moment. Veuillez vérifier le fichier JSON.")
    st.stop()

# --------------------------------------------------------------------------- #
# Menu & Filtres
# --------------------------------------------------------------------------- #

st.title("🏛️ Votes de l'Assemblée nationale")

with st.sidebar:
    st.header("Filtres")
    mot_cle = st.text_input("Rechercher un mot-clé", placeholder="ex : budget, immigration, santé…")
    only_final = st.checkbox(
        "Uniquement les votes d'ensemble",
        value=True,
    )

# Filtrage des scrutins
filtered_scrutins = []
for s in scrutins:
    titre_norm = normalize(s.get("titre", ""))
    
    if only_final and "ensemble" not in titre_norm:
        continue
    if mot_cle and normalize(mot_cle) not in titre_norm:
        continue
        
    filtered_scrutins.append(s)

if not filtered_scrutins:
    st.warning("Aucun scrutin ne correspond à votre recherche.")
    st.stop()

# Sélecteur : affiche uniquement le titre (sans date ni numéro)
def format_titre_seul(scrutin) -> str:
    titre = scrutin.get("titre", "Scrutin sans titre")
    return titre[:120] + "..." if len(titre) > 120 else titre

index_choisi = st.selectbox(
    "Sélectionnez un projet / proposition de loi :",
    options=range(len(filtered_scrutins)),
    format_func=lambda idx: format_titre_seul(filtered_scrutins[idx])
)

vote = filtered_scrutins[index_choisi]

# --------------------------------------------------------------------------- #
# Affichage du Scrutin Sélectionné
# --------------------------------------------------------------------------- #

st.divider()
st.subheader(f"{vote.get('titre')}")

col_meta1, col_meta2, col_meta3 = st.columns(3)
col_meta1.write(f"**Scrutin n° :** {vote.get('numero')}")
col_meta2.write(f"**Date du vote :** {vote.get('date')}")

sort_info = str(vote.get("sort", "Non précisé"))
if "adopté" in sort_info.lower():
    col_meta3.success(f"**Résultat :** {sort_info}")
else:
    col_meta3.error(f"**Résultat :** {sort_info}")

if vote.get("demandeur"):
    st.caption(f"**Demandeur :** {vote.get('demandeur')}")

# Synthèse globale des voix
st.markdown("### 📊 Synthèse globale du vote")
synthese = vote.get("syntheseVote", {})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pour 🟩", synthese.get("pour", 0))
col2.metric("Contre 🟥", synthese.get("contre", 0))
col3.metric("Abstentions 🟧", synthese.get("abstention", 0))
col4.metric("Total Votants 👥", synthese.get("total", 0))

# --------------------------------------------------------------------------- #
# Graphique en barres par Groupe Politique
# --------------------------------------------------------------------------- #


st.divider()
st.markdown("### 🏛️ Répartition des votes par groupe politique")

groupes_data = vote.get("groupes", [])

if not groupes_data:
    st.info("Le détail par groupe politique n'est pas disponible pour ce scrutin.")
else:
    df_chart = pd.DataFrame(groupes_data)
    
    # Si les sigles sont des codes PO..., on tente un mapping de secours
    MAP_SECOURS = {
        "PO845401": "RN", "PO845407": "EPR", "PO845413": "LFI-NFP",
        "PO845419": "SOC", "PO845425": "DR", "PO845439": "EcoS",
        "PO845454": "Dem", "PO845470": "HOR", "PO845485": "LIOT",
        "PO845514": "GDR", "PO872880": "UDR", "PO840056": "NI"
    }
    if "sigle" in df_chart.columns:
        df_chart["sigle"] = df_chart["sigle"].apply(lambda x: MAP_SECOURS.get(x, x))
        df_chart = df_chart.set_index("sigle")[["pour", "contre", "abstention"]]
        
        st.bar_chart(
            df_chart,
            color=["#2ecc71", "#e74c3c", "#f39c12"],
            height=400
        )
