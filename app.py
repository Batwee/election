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
# Affichage de la Synthèse et du Graphique
# --------------------------------------------------------------------------- #

groupes_data = vote.get("groupes", [])
synthese = vote.get("syntheseVote", {})

# Calcul de secours si syntheseVote est à 0 dans le JSON
pour_tot = synthese.get("pour", 0)
contre_tot = synthese.get("contre", 0)
abst_tot = synthese.get("abstention", 0)

if pour_tot == 0 and contre_tot == 0 and abst_tot == 0 and groupes_data:
    pour_tot = sum(g.get("pour", 0) for g in groupes_data)
    contre_tot = sum(g.get("contre", 0) for g in groupes_data)
    abst_tot = sum(g.get("abstention", 0) for g in groupes_data)

total_votants = synthese.get("total", 0) or (pour_tot + contre_tot + abst_tot)

st.markdown("### 📊 Synthèse globale du vote")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pour 🟩", pour_tot)
col2.metric("Contre 🟥", contre_tot)
col3.metric("Abstentions 🟧", abst_tot)
col4.metric("Total Votants 👥", total_votants)

st.divider()
st.markdown("### 🏛️ Répartition des votes par groupe politique")

if not groupes_data:
    st.info("Le détail par groupe politique n'est pas disponible pour ce scrutin.")
else:
    df_chart = pd.DataFrame(groupes_data)

    # Conversion des codes PO... si jamais le script update.js n'a pas tourné
    MAP_SECOURS = {
        "PO845401": "RN", "PO845407": "EPR", "PO845413": "LFI-NFP",
        "PO845419": "SOC", "PO845425": "DR", "PO845439": "EcoS",
        "PO845454": "Dem", "PO845470": "HOR", "PO845485": "LIOT",
        "PO845514": "GDR", "PO872880": "UDR", "PO840056": "NI"
    }

    if "sigle" in df_chart.columns:
        df_chart["sigle"] = df_chart["sigle"].apply(lambda x: MAP_SECOURS.get(x, x))
        
        # On ne conserve que les colonnes utiles
        df_chart = df_chart.set_index("sigle")[["pour", "contre", "abstention"]]
        
        # Filtre : on retire les groupes qui n'ont aucun votant sur ce scrutin
        df_chart["total_groupe"] = df_chart["pour"] + df_chart["contre"] + df_chart["abstention"]
        df_chart = df_chart[df_chart["total_groupe"] > 0].drop(columns=["total_groupe"])

        if not df_chart.empty:
            st.bar_chart(
                df_chart,
                color=["#2ecc71", "#e74c3c", "#f39c12"],
                height=400
            )
        else:
            st.info("Aucun vote enregistré parmi les groupes pour ce scrutin.")
    else:
        st.warning("Structure des groupes invalide dans les données.")
