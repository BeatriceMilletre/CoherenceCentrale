import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================
# CONFIG GÉNÉRALE
# ==========================
st.set_page_config(
    page_title="Questionnaire Cohérence Centrale",
    page_icon="🧩",
    layout="wide",
)

# ==========================
# PARAMÈTRES EMAIL / FICHIER
# (récupérés via st.secrets sur Streamlit Cloud)
# ==========================
EMAIL_SENDER = st.secrets["EMAIL_SENDER"]
EMAIL_APP_PASSWORD = st.secrets["EMAIL_APP_PASSWORD"]
PRACTITIONER_EMAIL = st.secrets["PRACTITIONER_EMAIL"]

DATA_FILE = "ecc_data.csv"  # fichier local de stockage des réponses


# ==========================
# FONCTION D’ENVOI D’EMAIL
# ==========================
def send_email_to_practitioner(code, total_score, subscales, meta_info):
    """
    Envoie un email au praticien avec le code de questionnaire et les scores.
    meta_info : dict (date, prénom/pseudo, âge, email patient éventuel)
    """
    try:
        subject = f"[ECC] Nouvelle passation – Code {code}"
        body_lines = [
            "Une nouvelle passation du questionnaire Cohérence Centrale (ECC-24) a été enregistrée.",
            "",
            f"Code questionnaire : {code}",
            f"Date et heure : {meta_info.get('timestamp', 'N/A')}",
            f"Prénom/Pseudo : {meta_info.get('prenom', 'N/A')}",
            f"Âge : {meta_info.get('age', 'N/A')}",
            f"Email patient : {meta_info.get('email_patient', 'N/A')}",
            "",
            f"Score total : {total_score}",
            "",
            "Sous-scores (non communiqués au patient) :",
            f"- Préférence pour les détails (items 1–6) : {subscales['A_details']}",
            f"- Intégration globale (items 7–12) : {subscales['B_global']}",
            f"- Sensibilité au contexte (items 13–18) : {subscales['C_context']}",
            f"- Flexibilité globale-locale (items 19–24) : {subscales['D_flexibility']}",
            "",
            "Pour consulter le détail des réponses, connectez-vous à l’application en mode Praticien",
            "et saisissez le code ci-dessus.",
        ]
        body = "\n".join(body_lines)

        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = PRACTITIONER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        st.error(f"Erreur lors de l'envoi de l'email au praticien : {e}")


# ==========================
# ITEMS DU QUESTIONNAIRE ECC-24
# ==========================
ECC_ITEMS = {
    1: "Lorsque je regarde une scène ou une image, je remarque d’abord les petits détails avant l’ensemble.",
    2: "Je me concentre très facilement sur un élément précis, même si cela me fait perdre de vue le reste.",
    3: "Les petites erreurs (un mot mal placé, un bruit, un détail visuel) attirent immédiatement mon attention.",
    4: "Je remarque souvent des détails que les autres ne voient pas.",
    5: "Quand j’écoute quelqu’un, je retiens surtout des éléments précis et moins l’idée générale.",
    6: "Les tâches demandant une analyse minutieuse me paraissent plus naturelles que celles demandant une vision globale.",
    7: "J’ai parfois du mal à comprendre l’idée principale d’un texte si je dois lire rapidement.",
    8: "Je peux passer beaucoup de temps à me focaliser sur une partie d’un problème sans voir la solution complète.",
    9: "Lorsque j’apprends quelque chose de nouveau, je me perds dans les détails au lieu d’avoir une vue d’ensemble.",
    10: "Je comprends souvent les règles ou consignes une par une, mais j’ai du mal à les rassembler en un plan global.",
    11: "Dans les conversations, je peux perdre de vue le sujet principal si un détail m’interpelle.",
    12: "J’ai besoin de plus de temps que les autres pour rassembler plusieurs informations en une idée cohérente.",
    13: "Je comprends littéralement ce qu’on dit, même quand les autres comprennent des sous-entendus.",
    14: "Lorsque le contexte change, j’ai du mal à adapter mon interprétation ou ma compréhension.",
    15: "Le sens d’une phrase ambiguë n’est pas évident pour moi sans explication supplémentaire.",
    16: "Je me fie plus volontiers à ce que je vois ou entends exactement qu’à ce que la situation laisse penser.",
    17: "J’ai du mal à deviner l’intention globale d’une personne si je n’ai pas tous les détails.",
    18: "Je peux être déstabilisé·e si une information contradictoire apparaît dans une situation.",
    19: "Passer d’un travail sur les détails à une vision globale me demande un effort conscient.",
    20: "J’ai du mal à changer de méthode lorsque celle que j’utilise se révèle inefficace.",
    21: "Je me sens plus à l’aise dans des tâches structurées que dans des situations floues ou ouvertes.",
    22: "Il m’est difficile de résumer quelque chose sans avoir peur “d’oublier un détail important”.",
    23: "Quand je dois comprendre rapidement une situation, je me sens parfois submergé·e par trop d’informations à trier.",
    24: "Je préfère analyser les éléments un par un plutôt que de faire une interprétation globale.",
}


# ==========================
# UTILITAIRES SCORING
# ==========================
def compute_scores(responses_numeric):
    """
    responses_numeric : dict {item_index: score_int}
    Retourne total et sous-scores.
    """
    total_score = sum(responses_numeric.values())

    # Sous-échelles par tranches d’items
    A_details = sum(responses_numeric[i] for i in range(1, 7))        # 1–6
    B_global = sum(responses_numeric[i] for i in range(7, 13))       # 7–12
    C_context = sum(responses_numeric[i] for i in range(13, 19))     # 13–18
    D_flexibility = sum(responses_numeric[i] for i in range(19, 25)) # 19–24

    subscales = {
        "A_details": A_details,
        "B_global": B_global,
        "C_context": C_context,
        "D_flexibility": D_flexibility,
    }
    return total_score, subscales


def save_response(record):
    """
    Sauvegarde la réponse dans un CSV local.
    record : dict avec toutes les colonnes.
    """
    df_new = pd.DataFrame([record])

    if os.path.exists(DATA_FILE):
        try:
            df_old = pd.read_csv(DATA_FILE)
            df_all = pd.concat([df_old, df_new], ignore_index=True)
        except Exception:
            df_all = df_new
    else:
        df_all = df_new

    df_all.to_csv(DATA_FILE, index=False)


def load_response_by_code(code):
    """
    Charge la ligne correspondant au code.
    Retourne None si non trouvé.
    """
    if not os.path.exists(DATA_FILE):
        return None

    df = pd.read_csv(DATA_FILE)
    sub = df[df["code"] == code]
    if sub.empty:
        return None
    return sub.iloc[0]


def interpret_total_score(total_score):
    """
    Interprétation indicative, pour le praticien.
    """
    if total_score <= 20:
        return "Cohérence centrale très forte (vision globale dominante)."
    elif total_score <= 40:
        return "Cohérence centrale plutôt globale."
    elif total_score <= 60:
        return "Équilibre globale / détails."
    elif total_score <= 80:
        return "Cohérence centrale plutôt locale (profil détailliste)."
    else:
        return "Cohérence centrale très locale / faible cohérence centrale."


# ==========================
# UI – SIDEBAR
# ==========================
st.sidebar.title("Navigation")
mode = st.sidebar.radio(
    "Choisissez votre espace :",
    ("Passation (patient)", "Espace praticien"),
)

st.sidebar.markdown("---")
st.sidebar.write("Questionnaire ECC-24 – Cohérence centrale.")


# ==========================
# MODE PATIENT
# ==========================
if mode == "Passation (patient)":
    st.title("🧩 Questionnaire sur votre manière de traiter les informations")

    st.write(
        """
Ce questionnaire vise à mieux comprendre **votre manière naturelle de percevoir et d’organiser les informations**.  
Il n’y a pas de bonne ou de mauvaise réponse. Répondez le plus honnêtement possible à partir de votre expérience habituelle.
"""
