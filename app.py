"""
App Streamlit — Votes de l'Assemblée nationale
================================================

Source de données : le fichier `votes.json` généré par le pipeline
https://github.com/Batwee/updatevotes (data.assemblee-nationale.fr),
lu directement depuis GitHub. Contrairement à une intégration basée sur
l'API NosDéputés.fr, tout le détail par groupe politique (sigle, position,
décompte des voix) est déjà présent dans le fichier : une seule requête
HTTP suffit pour toute la session, pas d'appel supplémentaire par scrutin.
"""

import unicodedata

import pandas as pd
import requests
import streamlit as st

# Adaptez le chemin si votre fichier est ailleurs dans le dépôt
# (ex. si vous générez une archive par législature : votes_16.json, votes_17.json...)
URL_API = "https://raw.githubusercontent.com/Batwee/updatevotes/main/votes.json"

@st.cache_data(ttl=3600)  # Mettre en cache pour éviter de re-télécharger à chaque clic
def load_votes():
    try:
        response = requests.get(URL_API)
        response.raise_for_status()
        data = response.json()
        
        # 'data' est déjà directement la liste des scrutins [ {...}, {...} ]
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Sécurité au cas où la structure évolue
            return data.get('scrutins', data.get('votes', []))
        return []
    except Exception as e:
        st.error(f"Impossible de récupérer la liste des scrutins : {e}")
        return []

# Chargement des données
votes = load_votes()

st.title("🏛️ Scrutins de l'Assemblée Nationale")
st.write(f"Nombre total de scrutins : {len(votes)}")

# Exemple de parcours des scrutins
if votes:
    # Affichage du dernier scrutin
    dernier_vote = votes[0]
    
    st.subheader(f"Scrutin n°{dernier_vote.get('numero')} - {dernier_vote.get('titre')}")
    st.write(f"**Date :** {dernier_vote.get('date')}")
    st.write(f"**Résultat (Sort) :** {dernier_vote.get('sort')}")
    
    synthese = dernier_vote.get('syntheseVote', {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pour", synthese.get('pour', 0))
    col2.metric("Contre", synthese.get('contre', 0))
    col3.metric("Abstention", synthese.get('abstention', 0))
    col4.metric("Total", synthese.get('total', 0))


# --------------------------------------------------------------------------- #
# Chargement des données
# --------------------------------------------------------------------------- #

try:
    with st.spinner("Chargement des scrutins…"):
        meta, scrutins = load_votes()
except Exception as e:
    st.error(f"Impossible de récupérer la liste des scrutins : {e}")
    st.stop()

scrutins_df = build_filter_df(scrutins)
# Index numero -> enregistrement complet (synthese + groupes inclus)
scrutins_index = {s["numero"]: s for s in scrutins}

st.title("Votes de l'Assemblée nationale")
st.caption(
    f"Législature {meta['legislature']} — {meta['count']} scrutins — "
    f"mis à jour le {meta['generated_at']}"
)

# --------------------------------------------------------------------------- #
# Filtres
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.header("Filtre")
    mot_cle = st.text_input("Mot-clé de la loi", placeholder="ex : immigration, retraite, budget…")
    only_final = st.checkbox(
        "Ne garder que les votes sur l'ensemble du texte (résultat qui fait foi)",
        value=True,
    )
    st.caption(
        "La liste ne montre par défaut que les votes sur **l'ensemble du texte** "
        "(le scrutin qui fait foi pour une loi, pas les votes sur amendements)."
    )

filtered = scrutins_df.copy()

if only_final:
    filtered = filtered[filtered["titre"].apply(lambda t: normalize("l'ensemble") in normalize(t))]

if mot_cle:
    key = normalize(mot_cle)
    filtered = filtered[filtered["titre"].apply(lambda t: key in normalize(t))]

filtered = filtered.sort_values("date", ascending=False)

if filtered.empty:
    st.warning("Aucun scrutin ne correspond à ce filtre. Essayez un autre mot-clé.")
    st.stop()


def label_for(row) -> str:
    date_str = row["date"].strftime("%d/%m/%Y") if pd.notna(row["date"]) else "date inconnue"
    return f"[{date_str}] {row['titre']}"


options = filtered.index.tolist()
choice_idx = st.selectbox(
    "Choisir une loi",
    options=options,
    format_func=lambda idx: label_for(filtered.loc[idx]),
)
numero = int(filtered.loc[choice_idx, "numero"])
scrutin = get_scrutin(scrutins_index, numero)

# --------------------------------------------------------------------------- #
# Détail du scrutin sélectionné
# --------------------------------------------------------------------------- #

st.subheader(f"Scrutin n°{numero}")
st.write(scrutin["titre"])

sort_info = scrutin.get("sort")
if sort_info:
    st.markdown(f"**Résultat : {sort_info}**")

synthese = scrutin.get("synthese", {})
col1, col2, col3, col4 = st.columns(4)
col1.metric("Votants", synthese.get("votants", 0))
col2.metric("Pour", synthese.get("pour", 0))
col3.metric("Contre", synthese.get("contre", 0))
col4.metric("Abstentions", synthese.get("abstentions", 0))

st.divider()
st.markdown("### Vote par groupe politique")

groupes = scrutin.get("groupes", [])
if not groupes:
    st.info("Aucun détail par groupe disponible pour ce scrutin.")
else:
    emoji = {"pour": "✅", "contre": "❌", "abstention": "➖"}
    for g in sorted(groupes, key=lambda g: g.get("sigle") or ""):
        icon = emoji.get(g.get("position"), "❔")
        st.write(
            f"{icon} **{g.get('sigle')}** ({g.get('nom', '')}) a voté "
            f"**{g.get('position', 'inconnu')}** — "
            f"{g.get('pour', 0)} pour / {g.get('contre', 0)} contre / "
            f"{g.get('abstentions', 0)} abstention(s)"
        )
