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
# ==========================
EMAIL_ENABLED = True
try:
    email_conf = st.secrets["email"]
    EMAIL_HOST = email_conf.get("host", "smtp.gmail.com")
    EMAIL_PORT = int(email_conf.get("port", 587))
    EMAIL_SENDER = email_conf.get("username")
    EMAIL_PASSWORD = email_conf.get("password")
    EMAIL_USE_TLS = bool(email_conf.get("use_tls", True))
    PRACTITIONER_EMAIL = EMAIL_SENDER  # même adresse par défaut
except Exception:
    EMAIL_ENABLED = False
    EMAIL_HOST = ""
    EMAIL_PORT = 0
    EMAIL_SENDER = ""
    EMAIL_PASSWORD = ""
    EMAIL_USE_TLS = False
    PRACTITIONER_EMAIL = ""

DATA_FILE = "ecc_data.csv"


# ==========================
# FONCTION D’ENVOI D’EMAIL
# ==========================
def send_email_to_practitioner(code, total_score, subscales, meta_info):
    """Envoie un email automatique au praticien (si configuré)."""

    if not EMAIL_ENABLED:
        return

    try:
        subject = f"[ECC] Nouvelle passation – Code {code}"

        body = (
            "Une nouvelle passation du questionnaire ECC-24 a été enregistrée.\n\n"
            f"Code : {code}\n"
            f"Date : {meta_info.get('timestamp', 'N/A')}\n"
            f"Prénom/pseudo : {meta_info.get('prenom', 'N/A')}\n"
            f"Âge : {meta_info.get('age', 'N/A')}\n"
            f"Email patient : {meta_info.get('email_patient', 'N/A')}\n\n"
            f"Score total : {total_score}\n\n"
            "Sous-scores :\n"
            f"- Préférence détails (1–6) : {subscales['A_details']}\n"
            f"- Intégration globale (7–12) : {subscales['B_global']}\n"
            f"- Sensibilité contexte (13–18) : {subscales['C_context']}\n"
            f"- Flexibilité globale-locale (19–24) : {subscales['D_flexibility']}\n\n"
            "Connectez-vous à l'espace praticien pour accéder aux réponses détaillées."
        )

        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = PRACTITIONER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        st.error(f"Erreur lors de l'envoi de l'email : {e}")


# ==========================
# ITEMS + CATÉGORIES
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

ITEM_CATEGORY = {}
for i in range(1, 7):
    ITEM_CATEGORY[i] = "Préférence pour les détails"
for i in range(7, 13):
    ITEM_CATEGORY[i] = "Difficulté d’intégration globale"
for i in range(13, 19):
    ITEM_CATEGORY[i] = "Sensibilité / résistance au contexte"
for i in range(19, 25):
    ITEM_CATEGORY[i] = "Flexibilité globale-locale"


# ==========================
# SCORING
# ==========================
def compute_scores(responses_numeric):
    # 24 items, échelle 0–3 → total 0–72, sous-scores 0–18
    total = sum(responses_numeric.values())
    A = sum(responses_numeric[i] for i in range(1, 7))
    B = sum(responses_numeric[i] for i in range(7, 13))
    C = sum(responses_numeric[i] for i in range(13, 19))
    D = sum(responses_numeric[i] for i in range(19, 25))

    return total, {
        "A_details": A,
        "B_global": B,
        "C_context": C,
        "D_flexibility": D,
    }


def interpret_total(total):
    """
    Renvoie une phrase de synthèse pour le degré de cohérence centrale.
    Seuils adaptés à un max de 72 (24 x 3) :
    anciens seuils 20/40/60/80 → 15/30/45/60.
    """
    if total <= 15:
        return "Niveau 1 – Cohérence centrale très forte (profil très global, centrage sur le sens et la gestalt)."
    if total <= 30:
        return "Niveau 2 – Cohérence centrale plutôt globale."
    if total <= 45:
        return "Niveau 3 – Équilibre global/local."
    if total <= 60:
        return "Niveau 4 – Cohérence centrale plutôt locale (profil détailliste)."
    return "Niveau 5 – Cohérence centrale très locale / faible cohérence centrale (traitement très fragmenté)."


# ==========================
# SAUVEGARDE CSV
# ==========================
def save_response(record):
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
    if not os.path.exists(DATA_FILE):
        return None
    df = pd.read_csv(DATA_FILE)
    sub = df[df["code"] == code]
    if sub.empty:
        return None
    return sub.iloc[0]


# ==========================
# UI — SIDEBAR
# ==========================
st.sidebar.title("Navigation")
mode = st.sidebar.radio(
    "Choisissez votre espace :",
    ("Passation (patient)", "Espace praticien"),
)


# ==========================
# MODE PATIENT
# ==========================
if mode == "Passation (patient)":

    st.title("🧩 Questionnaire – Cohérence centrale (ECC-24)")
    st.write(
        "Répondez selon votre fonctionnement habituel. Il n’y a pas de bonne ou de mauvaise réponse."
    )

    with st.form("ecc_form"):
        prenom = st.text_input("Prénom / Pseudo (facultatif)")
        age = st.number_input("Âge", min_value=8, max_value=99, value=18)
        email_patient = st.text_input("Email (facultatif)")

        st.markdown("---")
        st.subheader("Questions")

        # 4 degrés de réponse (0–3)
        labels = ["Jamais", "Parfois", "Souvent", "Toujours"]
        score_map = {"Jamais": 0, "Parfois": 1, "Souvent": 2, "Toujours": 3}

        raw = {}
        for i in range(1, 25):
            raw[i] = st.radio(
                f"{i}. {ECC_ITEMS[i]}",
                labels,
                index=None,  # pas de valeur par défaut → obligation de réponse
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

            rec = {
                "timestamp": ts,
                "code": code,
                "prenom": prenom,
                "age": age,
                "email_patient": email_patient,
                "total_score": total,
                "A_details": subs["A_details"],
                "B_global": subs["B_global"],
                "C_context": subs["C_context"],
                "D_flexibility": subs["D_flexibility"],
            }

            for i in range(1, 25):
                rec[f"Q{i}_score"] = numeric[i]
                rec[f"Q{i}_label"] = raw[i]

            save_response(rec)

            meta = {"timestamp": ts, "prenom": prenom, "age": age, "email_patient": email_patient}
            send_email_to_practitioner(code, total, subs, meta)

            st.success("Réponses enregistrées.")
            st.info(f"Votre code à transmettre au praticien : **{code}**")

            st.write(
                "Ce questionnaire ne constitue pas un diagnostic. "
                "Les résultats doivent être interprétés par un professionnel dans le cadre d’un entretien clinique."
            )


# ==========================
# MODE PRATICIEN
# ==========================
elif mode == "Espace praticien":

    st.title("👩‍⚕️ Espace praticien – Cohérence centrale")

    code_input = st.text_input("Code questionnaire du patient")

    if st.button("Charger"):
        code_clean = code_input.strip()
        if not code_clean:
            st.error("Merci de saisir un code.")
        else:
            row = load_response_by_code(code_clean)

            if row is None:
                st.error("Aucune passation trouvée pour ce code.")
            else:
                st.success("Passation trouvée.")

                numeric = {}
                labels_raw = {}
                for i in range(1, 25):
                    sc = f"Q{i}_score"
                    lb = f"Q{i}_label"
                    numeric[i] = int(row[sc])
                    labels_raw[i] = row[lb]

                total, subs = compute_scores(numeric)

                st.subheader("Informations générales")
                st.write(f"Date : {row['timestamp']}")
                st.write(f"Prénom/pseudo : {row['prenom']}")
                st.write(f"Âge : {row['age']}")
                st.write(f"Email patient : {row['email_patient']}")

                st.markdown("---")
                st.subheader("Scores globaux")

                st.metric("Score total (0–72)", total)
                st.write(interpret_total(total))

                st.markdown("**Sous-scores par dimension (0–18)**")
                st.write(f"- Préférence pour les détails (items 1–6) : {subs['A_details']} / 18")
                st.write(f"- Difficulté d’intégration globale (7–12) : {subs['B_global']} / 18")
                st.write(f"- Sensibilité / résistance au contexte (13–18) : {subs['C_context']} / 18")
                st.write(f"- Flexibilité globale-locale (19–24) : {subs['D_flexibility']} / 18")

                st.markdown(
                    "_Plus le score total et les sous-scores sont élevés, plus le style de traitement est local, "
                    "détailliste, avec une cohérence centrale faible. À lire en fonction du profil global (TSA, HPI, anxiété, etc.)._"
                )

                st.markdown("---")
                st.subheader("Détail des réponses par item et par catégorie")

                df = pd.DataFrame(
                    [
                        {
                            "Item": i,
                            "Catégorie": ITEM_CATEGORY[i],
                            "Énoncé": ECC_ITEMS[i],
                            "Réponse": labels_raw[i],
                            "Score (0–3)": numeric[i],
                        }
                        for i in range(1, 25)
                    ]
                )

                # tri par catégorie puis item
                df = df.sort_values(by=["Catégorie", "Item"]).reset_index(drop=True)

                st.dataframe(df, use_container_width=True)

                st.markdown(
                    "Ce questionnaire explore le style de traitement de l’information (global vs local). "
                    "Il ne remplace ni un bilan neuropsychologique, ni un diagnostic, mais peut étayer vos hypothèses cliniques."
                )
