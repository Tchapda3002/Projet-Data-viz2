import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import random
from datetime import date, timedelta
from unidecode import unidecode

from database import SessionLocal, engine, Base
from models import Teacher, Student, Course, Session, Attendance, Grade

dash.register_page(__name__, path="/init", name="Initialisation")

# --- Fonctions d'import ---

def parse_teachers(df_maquette):
    """Extrait les enseignants uniques depuis la feuille MAQUETTE."""
    teachers = {}
    is_semestre6_swapped = False

    for _, row in df_maquette.iterrows():
        intitule = str(row.get("Intitulés des UE et des enseignements", ""))
        if "SEMESTRE 6" in intitule.upper():
            is_semestre6_swapped = True
            continue

        enseignant = row.get("Enseignant", None)
        if pd.isna(enseignant) or enseignant in ("NaN", "Enseignant"):
            continue

        # Recuperer email et telephone de la ligne
        if is_semestre6_swapped:
            row_email = str(row.get("Téléphone", "")) if not pd.isna(row.get("Téléphone")) else None
            row_tel = str(row.get("Email", "")) if not pd.isna(row.get("Email")) else None
        else:
            row_email = str(row.get("Email", "")) if not pd.isna(row.get("Email")) else None
            row_tel = str(row.get("Téléphone", "")) if not pd.isna(row.get("Téléphone")) else None

        if row_tel:
            row_tel = str(row_tel).replace("+", "").replace(" ", "").split(".")[0]

        # Gerer les enseignants multiples (separes par /)
        noms_enseignants = str(enseignant).split("/")
        for i, nom_complet in enumerate(noms_enseignants):
            nom_complet = nom_complet.strip()
            if not nom_complet:
                continue

            parts = nom_complet.split()
            if len(parts) < 2:
                continue

            prenom = " ".join(parts[:-1])
            nom = parts[-1]

            if nom_complet not in teachers:
                # Si plusieurs enseignants partagent la meme ligne, generer un email unique pour le 2e
                if i == 0:
                    email = row_email
                    telephone = row_tel
                else:
                    email_prenom = unidecode(prenom.split()[0].lower())
                    email_nom = unidecode(nom.lower())
                    email = f"{email_prenom}.{email_nom}@univ.sn"
                    telephone = row_tel

                teachers[nom_complet] = {
                    "nom": nom,
                    "prenom": prenom,
                    "email": email,
                    "telephone": telephone,
                }
    return teachers


def parse_courses(df_maquette, teacher_map):
    """Extrait les cours (hors lignes UE/semestre/total) depuis MAQUETTE."""
    courses = []
    skip_keywords = ["UE :", "Semestre", "SEMESTRE", "Total", "Stage d'immersion",
                     "UE : Stage + Rédaction"]
    code_counter = {}
    is_semestre6_swapped = False

    for _, row in df_maquette.iterrows():
        intitule = str(row.get("Intitulés des UE et des enseignements", ""))
        if "SEMESTRE 6" in intitule.upper():
            is_semestre6_swapped = True

        if any(kw in intitule for kw in skip_keywords):
            continue
        if pd.isna(row.get("Volume horaire")) or row.get("Volume horaire", 0) == 0:
            continue

        enseignant = row.get("Enseignant", None)
        if pd.isna(enseignant) or enseignant in ("NaN", "Enseignant"):
            continue

        # Prendre le premier enseignant si multiple
        nom_enseignant = str(enseignant).split("/")[0].strip()
        teacher_id = teacher_map.get(nom_enseignant)
        if not teacher_id:
            continue

        # Generer un code cours
        mots = intitule.replace("(", "").replace(")", "").replace("–", "").split()
        prefix = "".join([m[0].upper() for m in mots[:3] if m[0].isalpha()])
        if not prefix:
            prefix = "CRS"
        if prefix not in code_counter:
            code_counter[prefix] = 0
        code_counter[prefix] += 1
        code = f"{prefix}{300 + code_counter[prefix]}"

        credits = row.get("Crédits", 1.0)
        if pd.isna(credits):
            credits = 1.0

        courses.append({
            "code": code,
            "libelle": intitule.strip(),
            "volume_horaire": float(row["Volume horaire"]),
            "credits": float(credits),
            "teacher_id": teacher_id,
        })
    return courses


def parse_students(df_students):
    """Extrait les etudiants depuis la liste de classe."""
    students = []
    for _, row in df_students.iterrows():
        nom = str(row.get("Nom", "")).strip()
        prenom = str(row.get("Prénoms", "")).strip()
        if not nom or not prenom:
            continue

        # Generer email a partir du nom/prenom
        email_prenom = unidecode(prenom.split()[0].lower())
        email_nom = unidecode(nom.lower())
        email = f"{email_prenom}.{email_nom}@univ.sn"

        # Date de naissance aleatoire (entre 20 et 25 ans)
        age = random.randint(20, 25)
        dob = date.today().replace(year=date.today().year - age) - timedelta(days=random.randint(0, 365))

        students.append({
            "nom": nom,
            "prenom": prenom,
            "email": email,
            "date_naissance": dob,
        })
    return students


def generate_sessions(courses, nb_per_course=3):
    """Genere des seances fictives pour chaque cours."""
    sessions = []
    themes_generiques = ["Introduction", "Cours magistral", "Exercices pratiques",
                         "Etude de cas", "Revision"]
    for course in courses:
        for i in range(nb_per_course):
            s_date = date(2025, 9, 1) + timedelta(weeks=i * 2, days=random.randint(0, 4))
            sessions.append({
                "course_code": course["code"],
                "date": s_date,
                "duree": round(random.choice([1.5, 2.0, 3.0]), 1),
                "theme": themes_generiques[i % len(themes_generiques)],
            })
    return sessions


def generate_attendance(session_ids, student_ids):
    """Genere des presences (environ 85% de presence)."""
    records = []
    for sid in session_ids:
        for stud_id in student_ids:
            if random.random() < 0.85:
                records.append({"session_id": sid, "student_id": stud_id})
    return records


def generate_grades(student_ids, courses):
    """Genere des notes aleatoires pour chaque etudiant/cours."""
    records = []
    for stud_id in student_ids:
        for course in courses:
            note = round(random.uniform(5, 18), 1)
            records.append({
                "student_id": stud_id,
                "course_code": course["code"],
                "note": note,
            })
    return records


def run_import():
    """Execute l'import complet des donnees Excel + generation."""
    db = SessionLocal()
    try:
        # Reset des tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        # 1. Lire les fichiers Excel
        df_maquette = pd.read_excel("Copie de matières_AS3.xlsx", sheet_name="MAQUETTE")
        df_students = pd.read_excel("Liste de classe AS3.xlsx")

        # 2. Importer les enseignants
        teachers_data = parse_teachers(df_maquette)
        teacher_map = {}
        for nom_complet, data in teachers_data.items():
            teacher = Teacher(**data)
            db.add(teacher)
            db.flush()
            teacher_map[nom_complet] = teacher.id
        db.commit()

        # 3. Importer les cours
        courses_data = parse_courses(df_maquette, teacher_map)
        for c in courses_data:
            db.add(Course(**c))
        db.commit()

        # 4. Importer les etudiants
        students_data = parse_students(df_students)
        for s in students_data:
            db.add(Student(**s))
        db.commit()

        # 5. Generer les seances
        sessions_data = generate_sessions(courses_data)
        for s in sessions_data:
            db.add(Session(**s))
        db.commit()

        # 6. Recuperer les IDs
        all_sessions = db.query(Session).all()
        all_students = db.query(Student).all()
        session_ids = [s.id for s in all_sessions]
        student_ids = [s.id for s in all_students]

        # 7. Generer les presences
        attendance_data = generate_attendance(session_ids, student_ids)
        for a in attendance_data:
            db.add(Attendance(**a))
        db.commit()

        # 8. Generer les notes
        grades_data = generate_grades(student_ids, courses_data)
        for g in grades_data:
            db.add(Grade(**g))
        db.commit()

        stats = {
            "teachers": len(teachers_data),
            "students": len(students_data),
            "courses": len(courses_data),
            "sessions": len(sessions_data),
            "attendance": len(attendance_data),
            "grades": len(grades_data),
        }
        return True, stats

    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        db.close()


def get_db_stats():
    """Recupere les stats actuelles de la base."""
    db = SessionLocal()
    try:
        return {
            "teachers": db.query(Teacher).count(),
            "students": db.query(Student).count(),
            "courses": db.query(Course).count(),
            "sessions": db.query(Session).count(),
            "attendance": db.query(Attendance).count(),
            "grades": db.query(Grade).count(),
        }
    except Exception:
        return None
    finally:
        db.close()


# --- Layout ---

layout = html.Div([
    html.H1("Initialisation & Migration"),
    html.P("Importation des donnees Excel vers la base de donnees PostgreSQL."),

    html.Hr(),

    # Etat de la base
    html.H3("Etat de la base de donnees"),
    html.Div(id="db-stats"),

    html.Hr(),

    # Bouton d'import
    html.H3("Migration des donnees"),
    html.P("Importe les etudiants et cours depuis les fichiers Excel, "
           "puis genere les seances, presences et notes."),
    dbc.Button("Lancer l'import", id="btn-import", color="dark", className="me-2"),
    dcc.Loading(html.Div(id="import-result"), type="circle"),

    html.Hr(),

    # Apercu des donnees
    html.H3("Apercu des donnees"),
    dcc.Tabs(id="tabs-preview", value="tab-students", children=[
        dcc.Tab(label="Etudiants", value="tab-students"),
        dcc.Tab(label="Enseignants", value="tab-teachers"),
        dcc.Tab(label="Cours", value="tab-courses"),
    ]),
    html.Div(id="tab-content"),
])


# --- Callbacks ---

@callback(Output("db-stats", "children"), Input("import-result", "children"))
def update_stats(_):
    stats = get_db_stats()
    if stats is None:
        return dbc.Alert("Base de donnees non connectee.", color="warning")

    cards = []
    labels = {
        "teachers": "Enseignants",
        "students": "Etudiants",
        "courses": "Cours",
        "sessions": "Seances",
        "attendance": "Presences",
        "grades": "Notes",
    }
    for key, label in labels.items():
        cards.append(
            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H4(stats[key], className="card-title"),
                    html.P(label, className="card-text"),
                ])
            ]), width=2)
        )
    return dbc.Row(cards)


@callback(
    Output("import-result", "children"),
    Input("btn-import", "n_clicks"),
    prevent_initial_call=True,
)
def do_import(n_clicks):
    success, result = run_import()
    if success:
        return dbc.Alert(
            f"Import reussi : {result['teachers']} enseignants, "
            f"{result['students']} etudiants, {result['courses']} cours, "
            f"{result['sessions']} seances, {result['attendance']} presences, "
            f"{result['grades']} notes.",
            color="success",
        )
    return dbc.Alert(f"Erreur : {result}", color="danger")


@callback(Output("tab-content", "children"), Input("tabs-preview", "value"))
def render_tab(tab):
    db = SessionLocal()
    try:
        if tab == "tab-students":
            rows = db.query(Student).all()
            if not rows:
                return html.P("Aucun etudiant.")
            data = [{"ID": s.id, "Nom": s.nom, "Prenom": s.prenom,
                      "Email": s.email, "Date naiss.": str(s.date_naissance)} for s in rows]
        elif tab == "tab-teachers":
            rows = db.query(Teacher).all()
            if not rows:
                return html.P("Aucun enseignant.")
            data = [{"ID": t.id, "Nom": t.nom, "Prenom": t.prenom,
                      "Email": t.email or "", "Telephone": t.telephone or ""} for t in rows]
        elif tab == "tab-courses":
            rows = db.query(Course).all()
            if not rows:
                return html.P("Aucun cours.")
            data = [{"Code": c.code, "Libelle": c.libelle, "Volume H.": c.volume_horaire,
                      "Credits": c.credits, "Enseignant": c.teacher.nom + " " + c.teacher.prenom}
                     for c in rows]
        else:
            return html.P("")

        return dash_table.DataTable(
            data=data,
            columns=[{"name": k, "id": k} for k in data[0].keys()],
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": "#f7f6f3", "fontWeight": "600",
                          "border": "1px solid #e8e8e4"},
            style_cell={"textAlign": "left", "padding": "8px 12px",
                        "border": "1px solid #e8e8e4", "fontSize": "14px"},
            page_size=15,
        )
    finally:
        db.close()
