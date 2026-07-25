import unicodedata
import pandas as pd
import requests
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Votes Assemblée Nationale",
    page_icon="🏛️",
    layout="wide"
)

# URL de l'API hébergée sur GitHub / jsDelivr
URL_API = "https://cdn.jsdelivr.net/gh/Batwee/updatevotes@main/votes.json"

def normalize(text: str) -> str:
    """Normalise une chaîne de caractères (supprime les accents et met en minuscules)."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower()

@st.cache_data(ttl=3600)
def load_votes():
    """Charge la liste des votes depuis l'URL JSON."""
    try:
        response = requests.get(URL_API)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get('scrutins', data.get('votes', []))
        return []
    except Exception as e:
        st.error(f"Impossible de récupérer la liste des scrutins : {e}")
        return []

# --------------------------------------------------------------------------- #
# Chargement et préparation des données
# --------------------------------------------------------------------------- #

with st.spinner("Chargement des scrutins…"):
    scrutins = load_votes()

if not scrutins:
    st.warning("Aucune donnée disponible pour le moment.")
    st.stop()

# Transformation en DataFrame Pandas pour faciliter le filtrage
scrutins_df = pd.DataFrame(scrutins)
if "date" in scrutins_df.columns:
    scrutins_df["date_parsed"] = pd.to_datetime(scrutins_df["date"], errors="coerce")

# Indexation par numéro de scrutin
scrutins_index = {s["numero"]: s for s in scrutins}

# --------------------------------------------------------------------------- #
# Interface principale & Filtres
# --------------------------------------------------------------------------- #

st.title("🏛️ Votes de l'Assemblée nationale")
st.caption(f"{len(scrutins)} textes/lois récents enregistrés.")

with st.sidebar:
    st.header("Filtres")
    mot_cle = st.text_input("Mot-clé de la loi", placeholder="ex : budget, immigration, santé…")
    only_final = st.checkbox(
        "Ne garder que les votes sur l'ensemble du texte",
        value=True,
    )
    st.caption(
        "Filtrage sur **l'ensemble du texte** (le scrutin qui fait foi pour une loi)."
    )

filtered = scrutins_df.copy()

# Filtre : Votes sur l'ensemble du texte uniquement
if only_final and "titre" in filtered.columns:
    filtered = filtered[filtered["titre"].apply(lambda t: "ensemble" in normalize(str(t)))]

# Filtre : Recherche par mot-clé
if mot_cle and "titre" in filtered.columns:
    key = normalize(mot_cle)
    filtered = filtered[filtered["titre"].apply(lambda t: key in normalize(str(t)))]

# Tri par date ou numéro
if "date_parsed" in filtered.columns:
    filtered = filtered.sort_values("date_parsed", ascending=False)

if filtered.empty:
    st.warning("Aucun scrutin ne correspond à ce filtre. Essayez un autre mot-clé.")
    st.stop()

# --------------------------------------------------------------------------- #
# Sélection de la loi
# --------------------------------------------------------------------------- #

def label_for(row) -> str:
    date_str = str(row.get("date", "Date inconnue"))
    numero = row.get("numero", "")
    titre = row.get("titre", "")
    return f"[{date_str}] Scrutin n°{numero} - {titre[:90]}..."

options_indices = filtered.index.tolist()
choice_idx = st.selectbox(
    "Choisir un texte / vote :",
    options=options_indices,
    format_func=lambda idx: label_for(filtered.loc[idx]),
)

numero_selectionne = int(filtered.loc[choice_idx, "numero"])
scrutin = scrutins_index.get(numero_selectionne)

# --------------------------------------------------------------------------- #
# Détail du scrutin sélectionné
# --------------------------------------------------------------------------- #

st.divider()
st.subheader(f"Scrutin n°{scrutin.get('numero')} — {scrutin.get('titre')}")

col_meta1, col_meta2 = st.columns(2)
col_meta1.write(f"**Date du vote :** {scrutin.get('date', 'Inconnue')}")

sort_info = scrutin.get("sort", "Non précisé")
if "adopté" in sort_info.lower():
    col_meta2.success(f"**Résultat :** {sort_info}")
else:
    col_meta2.error(f"**Résultat :** {sort_info}")

if scrutin.get("demandeur"):
    st.caption(f"**Demandeur :** {scrutin.get('demandeur')}")

# Synthèse des voix
st.markdown("### 📊 Synthèse du vote")
synthese = scrutin.get("syntheseVote", {})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pour 🟩", synthese.get("pour", 0))
col2.metric("Contre 🟥", synthese.get("contre", 0))
col3.metric("Abstentions 🟧", synthese.get("abstention", 0))
col4.metric("Total Votants 👥", synthese.get("total", 0))

# Détail par groupe (s'il existe dans le JSON)
st.divider()
st.markdown("### 👥 Vote par groupe politique")

groupes = scrutin.get("groupes", [])
if not groupes:
    st.info("Le détail par groupe politique n'est pas activé ou disponible pour ce fichier JSON.")
else:
    emoji = {"pour": "✅", "contre": "❌", "abstention": "➖"}
    for g in sorted(groupes, key=lambda item: item.get("sigle") or ""):
        icon = emoji.get(str(g.get("position")).lower(), "❔")
        st.write(
            f"{icon} **{g.get('sigle')}** ({g.get('nom', '')}) — "
            f"**{g.get('position', 'inconnu')}** | "
            f"{g.get('pour', 0)} pour / {g.get('contre', 0)} contre / "
            f"{g.get('abstentions', 0)} abstention(s)"
        )
