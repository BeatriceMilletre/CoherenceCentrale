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
# (sur Streamlit Cloud, récupérés via st.secrets)
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

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as se_
