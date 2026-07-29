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
        "développement durable", "l'eau", "l'air", "déchets",
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

# Ordre politique strict de la gauche vers la droite pour le tri forcé du graphique
ORDRE_GROUPES = [
    "GDR", "LFI-NFP", "EcoS", "SOC", "Dem", "EPR", "HOR", "LIOT", "DR", "UDR", "RN", "NI"
]

URL_API = "https://raw.githubusercontent.com/Batwee/updatevotes/main/votes.json"

def normalize(text: str) -> str:
    """Supprime les accents et passe en minuscules pour faciliter la recherche."""
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()

@st.cache_data(ttl=3600)
def load_votes():
    """Charge le fichier JSON contenant les données de base des scrutins."""
    try:
        res = requests.get(URL_API)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return []

@st.cache_data(ttl=3600)
def load_clair_vote(numero_scrutin):
    """Interroge l'API clair.vote pour récupérer les données enrichies (mises au point / rectifications)."""
    try:
        url = f"https://clair.vote/api/v1/scrutins/{numero_scrutin}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data
    except Exception:
        pass
    return None

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
    
    options_themes = ["Tous les thèmes"] + list(THEMES.keys())
    theme_choisi = st.selectbox("Filtrer par thème :", options=options_themes)
    
    only_final = st.checkbox("Uniquement les votes d'ensemble", value=True)

# --------------------------------------------------------------------------- #
# Filtrage des Scrutins
# --------------------------------------------------------------------------- #

filtered_scrutins = []

for s in scrutins:
    titre_norm = normalize(s.get("titre", ""))
    
    if only_final and "ensemble" not in titre_norm:
        continue
    
    if theme_choisi != "Tous les thèmes":
        keywords = THEMES.get(theme_choisi, [])
        match = False
        mots_titre = titre_norm.split()
        
        for kw in keywords:
            kw_norm = normalize(kw)
            if " " in kw_norm:
                if kw_norm in titre_norm:
                    match = True
                    break
            else:
                if kw_norm in mots_titre:
                    match = True
                    break
                    
        if not match:
            continue
            
    filtered_scrutins.append(s)

if not filtered_scrutins:
    st.warning("Aucun scrutin ne correspond aux critères sélectionnés.")
    st.stop()

# --------------------------------------------------------------------------- #
# Sélecteur du Scrutin
# --------------------------------------------------------------------------- #

def format_titre_select(s) -> str:
    t = s.get("titre", "Scrutin sans titre")
    phrases_a_retirer = [
        "l'ensemble de la proposition de loi visant à",
        "l'ensemble du projet de loi visant à",
        "l'ensemble du projet de loi",
        "l'ensemble de la proposition de loi pour",
        "l'ensemble de la proposition de loi relative à",
        "l'ensemble du projet de loi sur",
        "(texte de la commission mixte paritaire)."
    ]
    
    for phrase in phrases_a_retirer:
        idx = t.lower().find(phrase.lower())
        while idx != -1:
            t = t[:idx] + t[idx + len(phrase):]
            idx = t.lower().find(phrase.lower())
            
    t = " ".join(t.split())
    return t[:130] + "..." if len(t) > 130 else t

st.write(f"**{len(filtered_scrutins)}** scrutin(s) disponible(s)")

index_choisi = st.selectbox(
    "Sélectionnez un projet / proposition de loi :",
    options=range(len(filtered_scrutins)),
    format_func=lambda i: format_titre_select(filtered_scrutins[i])
)

vote = filtered_scrutins[index_choisi]
numero_scrutin = vote.get("numero")

# Récupération des données via l'API clair.vote (contient sourceData avec misesAuPoint)
clair_data = load_clair_vote(numero_scrutin)

# --------------------------------------------------------------------------- #
# Détails du Scrutin Sélectionné
# --------------------------------------------------------------------------- #

st.divider()
st.subheader(vote.get("titre"))

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.write(f"**Scrutin n° :** {numero_scrutin}")
col_m2.write(f"**Date du vote :** {vote.get('date')}")

sort_info = str(vote.get("sort", "Non précisé"))
if "adopté" in sort_info.lower():
    col_m3.success(f"**Résultat :** {sort_info}")
else:
    col_m3.error(f"**Résultat :** {sort_info}")

if vote.get("demandeur"):
    st.caption(f"**Demandeur :** {vote.get('demandeur')}")

# --------------------------------------------------------------------------- #
# 1. Synthèse Globale Initiale (Fichier source de base)
# --------------------------------------------------------------------------- #

st.markdown("### 📊 Synthèse globale du vote (Brute)")
syn = vote.get("syntheseVote", {})

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pour 🟩", syn.get("pour", 0))
c2.metric("Contre 🟥", syn.get("contre", 0))
c3.metric("Abstentions 🟧", syn.get("abstention", 0))
c4.metric("Total Votants 👥", syn.get("total", 0))

# --------------------------------------------------------------------------- #
# 2. Synthèse Globale avec Rectifications (Clair vote)
# --------------------------------------------------------------------------- #
if clair_data and "sourceData" in clair_data:
    decompte_officiel = clair_data["sourceData"].get("syntheseVote", {}).get("decompte", {})
    if decompte_officiel:
        st.markdown("### 📊 Synthèse globale du vote (Clair vote : rectifications)")
        
        p_off = int(decompte_officiel.get("pour", 0))
        c_off = int(decompte_officiel.get("contre", 0))
        a_off = int(decompte_officiel.get("abstention", 0))
        t_off = int(decompte_officiel.get("nombreVotants", 0))
        
        co1, co2, co3, co4 = st.columns(4)
        co1.metric("Pour 🟩 (Officiel)", p_off)
        co2.metric("Contre 🟥 (Officiel)", c_off)
        co3.metric("Abstentions 🟧 (Officiel)", a_off)
        co4.metric("Total Votants 👥 (Officiel)", t_off)

# --------------------------------------------------------------------------- #
# Graphique 1 : Répartition initiale par groupe politique
# --------------------------------------------------------------------------- #

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
            groupes_presents = [g for g in ORDRE_GROUPES if g in df.index]
            autres_groupes = [g for g in df.index if g not in ORDRE_GROUPES]
            ordre_final = groupes_presents + autres_groupes

            df = df.reindex(ordre_final)
            df.index = pd.CategoricalIndex(df.index, categories=ordre_final, ordered=True)

            st.bar_chart(
                df,
                color=["#2ecc71", "#e74c3c", "#f39c12"],
                height=400
            )

# --------------------------------------------------------------------------- #
# Graphique 2 : Répartition des votes par groupe politique (Clair vote : rectifications)
# --------------------------------------------------------------------------- #
if clair_data and "sourceData" in clair_data:
    ventilation = clair_data["sourceData"].get("ventilationVotes", {}).get("organe", {}).get("groupes", {}).get("groupe", [])
    
    if ventilation:
        st.divider()
        st.markdown("### 🏛️ Répartition des votes par groupe politique (Clair vote : rectifications)")
        
        data_rectifiee = []
        for g_item in ventilation:
            # Récupération du sigle du groupe (souvent sous 'libelle' ou l'une des clés de l'objet)
            sigle_g = g_item.get("sigle") or g_item.get("libelle") or "Inconnu"
            decompte = g_item.get("vote", {}).get("decompteVoix", {})
            
            data_rectifiee.append({
                "sigle": sigle_g,
                "pour": int(decompte.get("pour", 0)),
                "contre": int(decompte.get("contre", 0)),
                "abstention": int(decompte.get("abstention", 0))
            })
            
        df_rect = pd.DataFrame(data_rectifiee)
        if not df_rect.empty and "sigle" in df_rect.columns:
            df_rect = df_rect.set_index("sigle")
            df_rect["total"] = df_rect["pour"] + df_rect["contre"] + df_rect["abstention"]
            df_rect = df_rect[df_rect["total"] > 0].drop(columns=["total"])
            
            if not df_rect.empty:
                groupes_presents_r = [g for g in ORDRE_GROUPES if g in df_rect.index]
                autres_groupes_r = [g for g in df_rect.index if g not in ORDRE_GROUPES]
                ordre_final_r = groupes_presents_r + autres_groupes_r

                df_rect = df_rect.reindex(ordre_final_r)
                df_rect.index = pd.CategoricalIndex(df_rect.index, categories=ordre_final_r, ordered=True)

                st.bar_chart(
                    df_rect,
                    color=["#2ecc71", "#e74c3c", "#f39c12"],
                    height=400
                )

# --------------------------------------------------------------------------- #
# Résumé, Liens et Détails Supplémentaires (API clair.vote)
# --------------------------------------------------------------------------- #

st.divider()
st.markdown("### 📄 Informations complémentaires et résumé (clair.vote)")

if clair_data:
    resume_ia = clair_data.get("resumeIA") or clair_data.get("resume") or clair_data.get("description")
    if resume_ia:
        st.markdown("#### 💡 Résumé de la loi")
        st.info(resume_ia)
    
    source_url = clair_data.get("sourceUrl") or clair_data.get("url") or f"https://www.assemblee-nationale.fr/dyn/17/scrutins/{numero_scrutin}"
    if source_url:
        st.markdown(f"🔗 **Lien officiel :** [Accéder à la source officielle sur l'Assemblée Nationale]({source_url})")

    votes_par_position = clair_data.get("votesByPosition")
    if votes_par_position and isinstance(votes_par_position, dict):
        st.markdown("#### 🔍 Ventilation détaillée par parlementaire")
        tab_p, tab_c, tab_a = st.tabs(["🟢 Pour", "🔴 Contre", "🟠 Abstention"])
        
        with tab_p:
            pours_list = votes_par_position.get("pour", [])
            if pours_list:
                df_p = pd.DataFrame([{
                    "Nom": f"{item.get('parlementaire', {}).get('prenom', '')} {item.get('parlementaire', {}).get('nom', '')}",
                    "Groupe": item.get('parlementaire', {}).get('groupe', {}).get('nom', 'N/C')
                } for item in pours_list[:50]])
                st.dataframe(df_p, use_container_width=True)
                if len(pours_list) > 50:
                    st.caption(f"Affichage limité à 50 députés sur {len(pours_list)} pour optimiser l'affichage.")
            else:
                st.write("Aucun détail disponible.")
                
        with tab_c:
            contres_list = votes_par_position.get("contre", [])
            if contres_list:
                df_c = pd.DataFrame([{
                    "Nom": f"{item.get('parlementaire', {}).get('prenom', '')} {item.get('parlementaire', {}).get('nom', '')}",
                    "Groupe": item.get('parlementaire', {}).get('groupe', {}).get('nom', 'N/C')
                } for item in contres_list[:50]])
                st.dataframe(df_c, use_container_width=True)
            else:
                st.write("Aucun détail disponible.")
                
        with tab_a:
            abst_list = votes_par_position.get("abstention", [])
            if abst_list:
                df_a = pd.DataFrame([{
                    "Nom": f"{item.get('parlementaire', {}).get('prenom', '')} {item.get('parlementaire', {}).get('nom', '')}",
                    "Groupe": item.get('parlementaire', {}).get('groupe', {}).get('nom', 'N/C')
                } for item in abst_list[:50]])
                st.dataframe(df_a, use_container_width=True)
            else:
                st.write("Aucun détail disponible.")
else:
    st.markdown(f"🔗 **Lien officiel AN :** [Consulter le scrutin n°{numero_scrutin} sur le site de l'Assemblée Nationale](https://www.assemblee-nationale.fr/dyn/17/scrutins/{numero_scrutin})")
    st.info("Les informations enrichies de l'API clair.vote ne sont pas disponibles pour ce scrutin spécifique.")
