import unicodedata
import pandas as pd
import requests
import streamlit as st

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Votes Assemblée Nationale",
    page_icon="🏛️",
    layout="wide"
)

# --------------------------------------------------------------------------- #
# Dictionnaire des Thèmes
# --------------------------------------------------------------------------- #
THEMES = {
    "Écologie": [
        "climat", "environnement", "écologie", "biodiversité",
        "pollution", "carbone", "renouvelable", "transition énergétique",
        "développement durable", "eau", "air", "déchets",
        "recyclage", "agriculture durable", "émissions"
    ],
    "Économie": [
        "économie", "budget", "finances", "fiscal", "fiscalité",
        "impôt", "taxe", "entreprise", "commerce", "industrie",
        "croissance", "inflation", "pib", "investissement",
        "consommation", "banque", "assurance", "crédit"
    ],
    "Travail et emploi": [
        "emploi", "travail", "salaires", "salaire", "smic",
        "chômage", "apprentissage", "formation", "reconversion",
        "contrat", "cdi", "cdd", "entrepreneur", "microentreprise",
        "syndicat", "temps de travail"
    ],
    "Santé": [
        "santé", "hôpital", "médecin", "médecins",
        "pharmacie", "médicament", "assurance maladie",
        "sécurité sociale", "covid", "vaccin", "maladie",
        "handicap", "ehpad", "soins", "urgence", "prévention"
    ],
    "Éducation": [
        "éducation", "école", "collège", "lycée", "université",
        "enseignement", "professeur", "enseignant", "élève",
        "étudiant", "bts", "master", "recherche", "apprentissage"
    ],
    "Transports": [
        "transport", "transports", "voiture", "automobile",
        "vélo", "cyclable", "bus", "tramway", "tram",
        "train", "sncf", "métro", "avion", "aéroport",
        "mobilité", "route", "autoroute", "péage",
        "stationnement", "permis de conduire"
    ],
    "Sécurité": [
        "sécurité", "police", "gendarmerie", "terrorisme",
        "délinquance", "justice", "prison", "armée",
        "défense", "cybersécurité", "renseignement",
        "criminalité", "violence"
    ],
    "Justice": [
        "justice", "tribunal", "juge", "procès",
        "avocat", "condamnation", "peine",
        "code pénal", "code civil", "magistrat"
    ],
    "Logement": [
        "logement", "immobilier", "location", "loyer",
        "bail", "propriétaire", "locataire",
        "construction", "urbanisme", "habitat",
        "copropriété", "apl"
    ],
    "Société": [
        "famille", "égalité", "discrimination", "laïcité",
        "citoyenneté", "jeunesse", "vieillesse",
        "retraite", "solidarité", "inclusion",
        "protection sociale"
    ],
    "Immigration": [
        "immigration", "asile", "réfugié", "étranger",
        "visa", "frontière", "naturalisation",
        "titre de séjour", "expulsion"
    ],
    "Agriculture": [
        "agriculture", "agriculteur", "élevage",
        "pêche", "forêt", "viticulture",
        "alimentation", "bio", "semence"
    ],
    "Numérique": [
        "numérique", "informatique", "internet",
        "intelligence artificielle", "ia",
        "cyber", "données", "rgpd",
        "algorithme", "logiciel", "cloud",
        "5g", "télécommunications"
    ],
    "Culture": [
        "culture", "patrimoine", "cinéma",
        "musique", "livre", "lecture",
        "bibliothèque", "spectacle",
        "audiovisuel", "presse", "média"
    ],
    "Sport": [
        "sport", "olympique", "football",
        "rugby", "tennis", "association sportive",
        "stade", "club", "dopage"
    ],
    "Europe et international": [
        "union européenne", "europe",
        "commission européenne", "otan",
        "onu", "international",
        "coopération", "traité",
        "diplomatie", "accord"
    ],
    "Outre-mer": [
        "outre-mer", "guadeloupe",
        "martinique", "guyane",
        "la réunion", "mayotte",
        "polynésie", "nouvelle-calédonie"
    ],
    "Collectivités territoriales": [
        "commune", "mairie", "département",
        "région", "collectivité",
        "intercommunalité", "métropole",
        "territoire", "décentralisation"
    ],
    "Fiscalité": [
        "impôt", "tva", "taxe",
        "fiscalité", "revenu",
        "patrimoine", "succession",
        "donation", "niche fiscale"
    ],
    "Énergie": [
        "énergie", "électricité",
        "gaz", "nucléaire",
        "éolien", "solaire",
        "hydrogène", "hydraulique",
        "réacteur", "edf"
    ]
}

URL_API = "https://raw.githubusercontent.com/Batwee/updatevotes/main/votes.json"

def normalize(text: str) -> str:
    """Supprime les accents et passe en minuscules pour faciliter la recherche."""
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()

@st.cache_data(ttl=3600)
def load_votes():
    """Charge le fichier JSON contenant les données des scrutins."""
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
# Barre Latérale - Filtres
# --------------------------------------------------------------------------- #

st.title("🏛️ Votes de l'Assemblée nationale")

with st.sidebar:
    st.header("Filtres")
    
    # Filtre par Thème
    options_themes = ["Tous les thèmes"] + list(THEMES.keys())
    theme_choisi = st.selectbox("Filtrer par thème :", options=options_themes)
    
    # Filtre par type de vote
    only_final = st.checkbox("Uniquement les votes d'ensemble", value=True)

# --------------------------------------------------------------------------- #
# Filtrage des Scrutins
# --------------------------------------------------------------------------- #

filtered_scrutins = []

for s in scrutins:
    titre_norm = normalize(s.get("titre", ""))
    
    # 1. Filtre 'Vote d'ensemble'
    if only_final and "ensemble" not in titre_norm:
        continue
    
    # 2. Filtre par Thème
    if theme_choisi != "Tous les thèmes":
        keywords = THEMES.get(theme_choisi, [])
        match = any(normalize(kw) in titre_norm for kw in keywords)
        if not match:
            continue
            
    filtered_scrutins.append(s)

if not filtered_scrutins:
    st.warning("Aucun scrutin ne correspond aux critères sélectionnés.")
    st.stop()

# --------------------------------------------------------------------------- #
# Sélecteur du Scrutin
# --------------------------------------------------------------------------- #

def format_titre(s) -> str:
    """Affiche uniquement le titre du texte de loi dans la sélection."""
    t = s.get("titre", "Scrutin sans titre")
    return t[:130] + "..." if len(t) > 130 else t

st.write(f"**{len(filtered_scrutins)}** scrutin(s) disponible(s)")

index_choisi = st.selectbox(
    "Sélectionnez un projet / proposition de loi :",
    options=range(len(filtered_scrutins)),
    format_func=lambda i: format_titre(filtered_scrutins[i])
)

vote = filtered_scrutins[index_choisi]

# --------------------------------------------------------------------------- #
# Détails du Scrutin Sélectionné
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

# --------------------------------------------------------------------------- #
# Synthèse Globale des Votes
# --------------------------------------------------------------------------- #

st.markdown("### 📊 Synthèse globale du vote")
syn = vote.get("syntheseVote", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pour 🟩", syn.get("pour", 0))
c2.metric("Contre 🟥", syn.get("contre", 0))
c3.metric("Abstentions 🟧", syn.get("abstention", 0))
c4.metric("Total Votants 👥", syn.get("total", 0))

# --------------------------------------------------------------------------- #
# Graphique en Barres par Groupe Politique
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("### 🏛️ Répartition des votes par groupe politique")

groupes = vote.get("groupes", [])

if not groupes:
    st.info("Le détail par groupe politique n'est pas disponible pour ce scrutin.")
else:
    df = pd.DataFrame(groupes)
    
    if "sigle" in df.columns:
        # Configuration des colonnes et exclusion des groupes sans votants
        df = df.set_index("sigle")[["pour", "contre", "abstention"]]
        df["total"] = df["pour"] + df["contre"] + df["abstention"]
        df = df[df["total"] > 0].drop(columns=["total"])

        if not df.empty:
            st.bar_chart(
                df,
                color=["#2ecc71", "#e74c3c", "#f39c12"],  # Vert (Pour), Rouge (Contre), Orange (Abstention)
                height=400
            )
        else:
            st.info("Aucun vote enregistré parmi les groupes pour ce scrutin.")
    else:
        st.warning("Format des données des groupes incorrect.")
