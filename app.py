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
EMAIL_SENDER = "beatricemilletre@gmail.com"           # expéditeur (Gmail)
EMAIL_APP_PASSWORD = "kogr txhm bpkf wihb"           # mot de passe d’application Gmail
PRACTITIONER_EMAIL = "beatricemilletre@gmail.com"    # destinataire (praticien)

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
# (sans catégories visibles pour le patient)
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
    A_details = sum(responses_numeric[i] for i in range(1, 7))       # 1–6
    B_global = sum(responses_numeric[i] for i in range(7, 13))      # 7–12
    C_context = sum(responses_numeric[i] for i in range(13, 19))    # 13–18
    D_flexibility = sum(responses_numeric[i] for i in range(19, 25))# 19–24

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
            # Si souci de lecture, on repart à zéro pour ne pas tout bloquer
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
    )

    with st.form("ecc_patient_form"):
        st.subheader("Informations générales (facultatif)")

        prenom = st.text_input("Prénom ou pseudo (facultatif)")
        age = st.number_input("Âge", min_value=8, max_value=99, value=18, step=1)
        email_patient = st.text_input("Votre email (facultatif, non transmis à d’autres personnes)")

        st.markdown("---")
        st.subheader("Vos réponses")

        st.write(
            """
Pour chaque affirmation, cochez la réponse qui vous correspond le mieux en général.
"""
        )

        response_labels = [
            "Sélectionnez...",
            "Jamais",
            "Rarement",
            "Parfois",
            "Souvent",
            "Toujours",
        ]
        label_to_score = {
            "Jamais": 0,
            "Rarement": 1,
            "Parfois": 2,
            "Souvent": 3,
            "Toujours": 4,
        }

        responses_raw = {}
        for i in range(1, 25):
            question = ECC_ITEMS[i]
            choice = st.radio(
                f"{i}. {question}",
                response_labels,
                index=0,
                key=f"q{i}",
            )
            responses_raw[i] = choice

        submitted = st.form_submit_button("Envoyer mes réponses")

    if submitted:
        # Vérifier que tout est bien rempli
        if any(ans == "Sélectionnez..." for ans in responses_raw.values()):
            st.error("Merci de répondre à toutes les questions avant de valider.")
        else:
            # Conversion en scores numériques
            responses_numeric = {
                i: label_to_score[responses_raw[i]] for i in responses_raw
            }

            total_score, subscales = compute_scores(responses_numeric)

            # Génération d’un code unique
            code = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:4].upper()

            timestamp = datetime.now().isoformat(timespec="seconds")

            # Préparation de l’enregistrement
            record = {
                "timestamp": timestamp,
                "code": code,
                "prenom": prenom,
                "age": age,
                "email_patient": email_patient,
                "total_score": total_score,
                "A_details": subscales["A_details"],
                "B_global": subscales["B_global"],
                "C_context": subscales["C_context"],
                "D_flexibility": subscales["D_flexibility"],
            }

            # Ajout des réponses item par item
            for i in range(1, 25):
                record[f"Q{i}"] = responses_numeric[i]

            # Sauvegarde locale
            save_response(record)

            # Envoi email au praticien
            meta = {
                "timestamp": timestamp,
                "prenom": prenom,
                "age": age,
                "email_patient": email_patient,
            }
            send_email_to_practitioner(code, total_score, subscales, meta)

            # Feedback patient (sans sous-échelles, sans interprétation fine)
            st.success("Vos réponses ont été enregistrées.")

            st.info(
                f"""
Votre code questionnaire est : **{code}**  

Conservez ce code : il permettra à votre praticien de retrouver vos réponses et d’en discuter avec vous lors de la séance.
"""
            )

            st.write(
                """
Ce questionnaire ne constitue pas en soi un diagnostic.  
Les résultats doivent être interprétés par un professionnel formé, dans le cadre d’un entretien clinique.
"""
            )


# ==========================
# MODE PRATICIEN
# ==========================
elif mode == "Espace praticien":
    st.title("👩‍⚕️ Espace praticien – Cohérence centrale (ECC-24)")

    st.write(
        """
Cet espace vous permet de retrouver les passations réalisées à l’aide du **code questionnaire** communiqué par le patient.  
Vous pouvez consulter les réponses détaillées, les sous-scores et une interprétation indicative.
"""
    )

    code_input = st.text_input("Code questionnaire (fourni par le patient)")

    if st.button("Charger les résultats"):
        code_input = code_input.strip()
        if not code_input:
            st.error("Merci de saisir un code.")
        else:
            row = load_response_by_code(code_input)
            if row is None:
                st.error("Aucune passation trouvée pour ce code.")
            else:
                st.success("Passation trouvée.")

                # Affichage des métadonnées
                st.subheader("Informations générales")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Date** : {row.get('timestamp', 'N/A')}")
                    st.write(f"**Code** : {row.get('code', 'N/A')}")
                with col2:
                    st.write(f"**Prénom/pseudo** : {row.get('prenom', 'N/A')}")
                    st.write(f"**Âge** : {row.get('age', 'N/A')}")
                with col3:
                    st.write(f"**Email patient** : {row.get('email_patient', 'N/A')}")

                # Scores
                total_score = row["total_score"]
                A_details = row["A_details"]
                B_global = row["B_global"]
                C_context = row["C_context"]
                D_flexibility = row["D_flexibility"]

                st.markdown("---")
                st.subheader("Scores")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Score total ECC-24", f"{int(total_score)}")
                    st.write(interpret_total_score(total_score))
                with col_b:
                    st.write("**Sous-scores (0–24 chacun)**")
                    st.write(f"- Préférence pour les détails (1–6) : **{int(A_details)}**")
                    st.write(f"- Intégration globale (7–12) : **{int(B_global)}**")
                    st.write(f"- Sensibilité au contexte (13–18) : **{int(C_context)}**")
                    st.write(f"- Flexibilité globale-locale (19–24) : **{int(D_flexibility)}**")

                st.markdown(
                    """
*Plus le score est élevé, plus le style de traitement tend vers un profil détailliste / local.*  
À interpréter en regard du fonctionnement global (TSA, HPI, anxiété, etc.).
"""
                )

                # Détail des réponses
                st.markdown("---")
                st.subheader("Détail des réponses item par item")

                data_items = []
                for i in range(1, 25):
                    q_text = ECC_ITEMS[i]
                    score = int(row[f"Q{i}"])
                    data_items.append(
                        {
                            "Item": i,
                            "Énoncé": q_text,
                            "Score (0–4)": score,
                        }
                    )

                df_items = pd.DataFrame(data_items)
                st.dataframe(df_items, use_container_width=True)

                st.markdown(
                    """
**Rappel clinique** :  
Ce questionnaire est un outil d’exploration du style de traitement de l’information (global vs local).  
Il ne remplace ni une évaluation neuropsychologique ni un diagnostic, mais peut éclairer vos hypothèses cliniques, notamment en contexte TSA / HPI.
"""
                )
