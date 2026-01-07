import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid
import json
import smtplib
from email.message import EmailMessage
from typing import Tuple

# ==========================
# CONFIG GÉNÉRALE
# ==========================
st.set_page_config(
    page_title="Questionnaire Cohérence Centrale",
    page_icon="🧩",
    layout="wide",
)

# ==========================
# PARAMÈTRES EMAIL
# ==========================
EMAIL_ENABLED = True
try:
    email_conf = st.secrets["email"]
    EMAIL_HOST = email_conf.get("host")
    EMAIL_PORT = int(email_conf.get("port", 587))
    EMAIL_USERNAME = email_conf.get("username")
    EMAIL_PASSWORD = email_conf.get("password")
    EMAIL_USE_TLS = bool(email_conf.get("use_tls", True))
    PRACTITIONER_EMAIL = email_conf.get("practitioner", EMAIL_USERNAME)
except Exception:
    EMAIL_ENABLED = False
    EMAIL_HOST = ""
    EMAIL_PORT = 0
    EMAIL_USERNAME = ""
    EMAIL_PASSWORD = ""
    EMAIL_USE_TLS = False
    PRACTITIONER_EMAIL = ""

DATA_FILE = "ecc_data.csv"

# ==========================
# ENVOI EMAIL AVEC JSON
# ==========================
def send_results_by_email(
    code: str,
    payload: dict,
) -> Tuple[bool, str]:

    if not EMAIL_ENABLED:
        return False, "Email non configuré."

    try:
        msg = EmailMessage()
        msg["Subject"] = f"Cohérence centrale (ECC-24) – Nouvelle passation ({code})"
        msg["From"] = EMAIL_USERNAME
        msg["To"] = PRACTITIONER_EMAIL

        msg.set_content(
            "Une nouvelle passation du questionnaire Cohérence centrale (ECC-24) a été complétée.\n\n"
            f"Code : {code}\n"
            f"Date : {payload['meta']['timestamp']}\n\n"
            "Les données complètes sont jointes en pièce jointe (JSON).\n"
        )

        json_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")

        msg.add_attachment(
            json_bytes,
            maintype="application",
            subtype="json",
            filename=f"ecc24_{code}.json",
        )

        smtp = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=20)
        smtp.ehlo()
        if EMAIL_USE_TLS:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        smtp.send_message(msg)
        smtp.quit()

        return True, "Résultats envoyés automatiquement au praticien."

    except Exception as e:
        return False, f"Erreur email : {e}"

# ==========================
# ITEMS
# ==========================
ECC_ITEMS = {
    1: "Lorsque je regarde une scène ou une image, je remarque d’abord les petits détails avant l’ensemble.",
    2: "Je me concentre très facilement sur un élément précis.",
    3: "Les petites erreurs attirent immédiatement mon attention.",
    4: "Je remarque souvent des détails que les autres ne voient pas.",
    5: "Quand j’écoute quelqu’un, je retiens surtout des éléments précis.",
    6: "Les tâches demandant une analyse minutieuse me paraissent naturelles.",
    7: "J’ai parfois du mal à comprendre l’idée principale d’un texte lu rapidement.",
    8: "Je me focalise sur une partie d’un problème sans voir l’ensemble.",
    9: "Je me perds dans les détails lors d’un nouvel apprentissage.",
    10: "Je comprends les règles une par une mais j’ai du mal à les assembler.",
    11: "Je perds le fil d’une conversation si un détail m’interpelle.",
    12: "J’ai besoin de temps pour synthétiser plusieurs informations.",
    13: "Je comprends les phrases de manière littérale.",
    14: "Lorsque le contexte change, j’ai du mal à adapter ma compréhension.",
    15: "Je ne saisis pas facilement les phrases ambiguës.",
    16: "Je me fie plus aux mots exacts qu’au contexte.",
    17: "J’ai du mal à deviner l’intention globale d’une personne.",
    18: "Les contradictions dans une situation me déstabilisent.",
    19: "Passer des détails à la vision d’ensemble me demande un effort.",
    20: "J’ai du mal à changer de méthode quand elle ne fonctionne plus.",
    21: "Je préfère les tâches structurées aux situations floues.",
    22: "J’ai du mal à résumer sans peur d’oublier un détail.",
    23: "Je suis submergé(e) quand je dois comprendre rapidement une situation.",
    24: "Je préfère analyser séparément chaque élément.",
}

# ==========================
# SCORING
# ==========================
def compute_scores(responses_numeric):
    total = sum(responses_numeric.values())
    return total, {
        "A_details": sum(responses_numeric[i] for i in range(1, 7)),
        "B_global": sum(responses_numeric[i] for i in range(7, 13)),
        "C_context": sum(responses_numeric[i] for i in range(13, 19)),
        "D_flexibility": sum(responses_numeric[i] for i in range(19, 25)),
    }

# ==========================
# UI — MODE PATIENT
# ==========================
st.title("🧩 Questionnaire – Cohérence centrale (ECC-24)")
st.write("Répondez selon votre fonctionnement habituel.")

with st.form("ecc_form"):
    prenom = st.text_input("Prénom / Pseudo (facultatif)")
    age = st.number_input("Âge", min_value=8, max_value=99, value=18)
    email_patient = st.text_input("Email (facultatif)")

    st.markdown("---")
    labels = ["Jamais", "Parfois", "Souvent", "Toujours"]
    score_map = {"Jamais": 0, "Parfois": 1, "Souvent": 2, "Toujours": 3}

    raw = {}
    for i in range(1, 25):
        raw[i] = st.radio(
            f"{i}. {ECC_ITEMS[i]}",
            labels,
            index=None,
            key=f"q{i}",
        )

    submit = st.form_submit_button("Envoyer mes réponses")

if submit:
    if any(v is None for v in raw.values()):
        st.error("Merci de répondre à toutes les questions.")
    else:
        numeric = {i: score_map[raw[i]] for i in raw}
        total, subs = compute_scores(numeric)

        code = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:4].upper()
        ts = datetime.now().isoformat(timespec="seconds")

        payload = {
            "questionnaire": "ECC-24 – Cohérence centrale",
            "meta": {
                "code": code,
                "timestamp": ts,
                "prenom": prenom,
                "age": age,
                "email_patient": email_patient,
            },
            "scores": {
                "total": total,
                **subs,
            },
            "responses": {
                f"Q{i}": {
                    "label": raw[i],
                    "score": numeric[i],
                    "item": ECC_ITEMS[i],
                }
                for i in range(1, 25)
            },
        }

        ok, msg = send_results_by_email(code, payload)

        if ok:
            st.success("Réponses enregistrées et transmises au praticien.")
        else:
            st.error(msg)

        st.info(f"Code de passation : **{code}**")
        st.write(
            "Ce questionnaire ne constitue pas un diagnostic. "
            "Les résultats doivent être interprétés par un professionnel."
        )
