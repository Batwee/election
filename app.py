"""
Votes Assemblée Nationale — visualisation par groupe politique
================================================================

Source de données : API JSON gratuite de NosDéputés.fr (Regards Citoyens)
  - Liste des scrutins d'une législature :
        https://www.nosdeputes.fr/{legislature}/scrutins/json
  - Détail d'un scrutin (votes par groupe) :
        https://www.nosdeputes.fr/{legislature}/scrutin/{numero}/json

Usage :
    pip install -r requirements.txt
    streamlit run app.py
"""

import unicodedata
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE_URL = "https://www.nosdeputes.fr"

st.set_page_config(page_title="Votes Assemblée Nationale", page_icon="🇫🇷", layout="wide")


# ----------------------------------------------------------------------
# Utilitaires
# ----------------------------------------------------------------------
def normalize(text: str) -> str:
    """Minuscule + sans accents, pour un filtre insensible à la casse/accents."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


@st.cache_data(ttl=3600, show_spinner=False)
def get_scrutins(legislature: int) -> pd.DataFrame:
    """Récupère la liste (légère) de tous les scrutins d'une législature."""
    url = f"{BASE_URL}/{legislature}/scrutins/json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    # La clé racine peut être "scrutins" (liste) selon les versions de l'API.
    scrutins = data.get("scrutins", data) if isinstance(data, dict) else data

    rows = []
    for item in scrutins:
        s = item.get("scrutin", item)  # certains éléments sont enveloppés dans "scrutin"
        rows.append(
            {
                "numero": s.get("numero"),
                "date": s.get("date"),
                "titre": s.get("titre") or s.get("title") or "",
            }
        )
    df = pd.DataFrame(rows).dropna(subset=["numero"])
    df["numero"] = df["numero"].astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values("numero", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def get_scrutin_detail(legislature: int, numero: int) -> dict:
    """Récupère le détail d'un scrutin (résultat global + votes par groupe).

    L'API nosdeputes.fr renvoie parfois une erreur 500 ponctuelle (scrutin
    volumineux, service surchargé...) : on retente une fois avant d'abandonner.
    """
    url = f"{BASE_URL}/{legislature}/scrutin/{numero}/json"
    last_error = None
    for attempt in range(2):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data.get("scrutin", data)
        except Exception as e:
            last_error = e
    raise last_error


def _find_first(d: dict, candidates):
    """Cherche la première clé existante parmi plusieurs orthographes possibles."""
    for c in candidates:
        if c in d:
            return d[c]
    return None


def _as_count(value):
    """Convertit une valeur de vote (int, dict avec total, ou liste de votants) en entier."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        total = _find_first(value, ["total", "decompte", "nombre", "effectif", "count"])
        if total is not None:
            return _as_count(total)
        for key in ("votant", "votants", "depute", "deputes"):
            if key in value and isinstance(value[key], list):
                return len(value[key])
    if isinstance(value, list):
        return len(value)
    return 0


def extract_group_votes(scrutin: dict) -> pd.DataFrame:
    """
    Construit un DataFrame [groupe, pour, contre, abstention, non_votant]
    à partir du détail JSON d'un scrutin, en étant tolérant sur les noms de clés
    (l'API n'est pas toujours strictement documentée).
    """
    groupes = _find_first(scrutin, ["groupes", "groupes_votes", "ventilation_groupes"]) or []

    rows = []
    for g in groupes:
        nom = _find_first(g, ["nom", "libelle", "organisme", "groupe", "nom_groupe"]) or _find_first(
            g, ["sigle", "acronyme"]
        ) or "Inconnu"

        # Les décomptes peuvent être à plat dans le groupe, ou dans un sous-objet "votes"/"totaux".
        source = _find_first(g, ["votes", "totaux", "decompte"]) or g

        pour = _as_count(_find_first(source, ["pour", "pours", "pours_nombre", "nombre_pour"]))
        contre = _as_count(_find_first(source, ["contre", "contres", "nombre_contre"]))
        abstention = _as_count(
            _find_first(source, ["abstention", "abstentions", "nombre_abstention"])
        )
        non_votant = _as_count(
            _find_first(source, ["non_votant", "nonVotant", "nonVotants", "non_votants", "nombre_non_votant"])
        )

        rows.append(
            {
                "Groupe": nom,
                "Pour": pour,
                "Contre": contre,
                "Abstention": abstention,
                "Non-votant": non_votant,
            }
        )

    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Interface
# ----------------------------------------------------------------------
st.title("🇫🇷 Votes de l'Assemblée nationale par groupe politique")
st.caption("Données : API JSON de [NosDéputés.fr](https://www.nosdeputes.fr) (Regards Citoyens)")

with st.sidebar:
    st.header("Filtre")
    legislature = st.number_input("Législature", min_value=15, max_value=17, value=17, step=1)
    st.caption(
        "La liste ne montre que les votes sur **l'ensemble du texte** "
        "(le scrutin qui fait foi pour une loi, pas les votes sur amendements)."
    )

try:
    with st.spinner("Chargement de la liste des scrutins…"):
        scrutins_df = get_scrutins(legislature)
except Exception as e:
    st.error(f"Impossible de récupérer la liste des scrutins : {e}")
    st.stop()

# On ne garde que les votes finaux ("sur l'ensemble ...") : ce sont les scrutins
# qui font foi pour une loi donnée, un seul par texte adopté définitivement en séance.
lois_df = scrutins_df[
    scrutins_df["titre"].apply(lambda t: normalize("l'ensemble") in normalize(t))
].sort_values("date", ascending=False)

if lois_df.empty:
    st.warning("Aucun vote sur l'ensemble d'un texte n'a été trouvé pour cette législature.")
    st.stop()


def label_for(row) -> str:
    date_str = row["date"].strftime("%d/%m/%Y") if pd.notna(row["date"]) else "date inconnue"
    return f"[{date_str}] {row['titre']}"


options = lois_df.index.tolist()
choice_idx = st.selectbox(
    "Choisir une loi",
    options=options,
    format_func=lambda idx: label_for(lois_df.loc[idx]),
)

dernier = lois_df.loc[choice_idx]
numero = int(dernier["numero"])

st.subheader(f"Scrutin n°{numero}")
st.write(f"**{dernier['titre']}**")
if pd.notna(dernier["date"]):
    st.write(f"📅 {dernier['date'].strftime('%d/%m/%Y')}")

try:
    with st.spinner(f"Chargement du détail du scrutin n°{numero}…"):
        detail = get_scrutin_detail(legislature, numero)
except Exception as e:
    st.error(
        f"Impossible de récupérer le détail du scrutin n°{numero} : {e}\n\n"
        "Il s'agit souvent d'une erreur temporaire côté NosDéputés.fr "
        "(scrutin volumineux ou service surchargé) — essayez une autre loi "
        "dans la liste ou réessayez dans quelques instants."
    )
    st.stop()

sort_info = _find_first(detail, ["sort"])
sort_libelle = None
if isinstance(sort_info, dict):
    sort_libelle = _find_first(sort_info, ["libelle", "code"])
elif isinstance(sort_info, str):
    sort_libelle = sort_info
if sort_libelle:
    st.info(f"Résultat : **{sort_libelle}**")

votes_df = extract_group_votes(detail)

if votes_df.empty:
    st.warning(
        "La structure de la réponse de l'API n'a pas pu être interprétée automatiquement. "
        "Vous pouvez inspecter les données brutes ci-dessous pour ajuster le code."
    )
    with st.expander("Voir la réponse JSON brute"):
        st.json(detail)
    st.stop()

votes_df = votes_df.sort_values("Pour", ascending=False)

# ----------------------------------------------------------------------
# Graphique en barres
# ----------------------------------------------------------------------
fig = go.Figure()
colors = {"Pour": "#2ca02c", "Contre": "#d62728", "Abstention": "#7f7f7f", "Non-votant": "#c7c7c7"}
for col in ["Pour", "Contre", "Abstention", "Non-votant"]:
    fig.add_trace(go.Bar(name=col, x=votes_df["Groupe"], y=votes_df[col], marker_color=colors[col]))

fig.update_layout(
    barmode="group",
    title=f"Répartition des votes par groupe — scrutin n°{numero}",
    xaxis_title="Groupe politique",
    yaxis_title="Nombre de votes",
    legend_title="Position",
    height=550,
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("Voir le tableau des données"):
    st.dataframe(votes_df, use_container_width=True)

with st.expander("Voir la réponse JSON brute (debug)"):
    st.json(detail)