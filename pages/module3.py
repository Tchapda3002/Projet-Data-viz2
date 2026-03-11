import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import io
import base64

from sqlalchemy.orm import joinedload, subqueryload

from database import SessionLocal
from models import Student, Course, Grade, Attendance, Session

dash.register_page(__name__, path="/etudiants", name="Etudiants & Notes")


def get_students_summary():
    db = SessionLocal()
    try:
        students = db.query(Student).options(
            subqueryload(Student.grades).joinedload(Grade.course),
            subqueryload(Student.attendances),
        ).order_by(Student.nom).all()
        total_sessions = db.query(Session).count()
        data = []
        for s in students:
            # Moyenne generale ponderee
            if s.grades:
                total_points = sum(g.note * g.course.credits for g in s.grades)
                total_credits = sum(g.course.credits for g in s.grades)
                moyenne = round(total_points / total_credits, 2) if total_credits > 0 else 0
            else:
                moyenne = "-"

            # Taux de presence
            nb_presences = len(s.attendances)
            taux_presence = round((nb_presences / total_sessions) * 100, 1) if total_sessions > 0 else 0

            data.append({
                "id": s.id,
                "nom": s.nom,
                "prenom": s.prenom,
                "email": s.email,
                "moyenne": moyenne,
                "taux_presence": taux_presence,
            })
        return data
    finally:
        db.close()


def get_student_detail(student_id):
    db = SessionLocal()
    try:
        student = db.query(Student).options(
            subqueryload(Student.grades).joinedload(Grade.course),
            subqueryload(Student.attendances),
        ).filter_by(id=student_id).first()
        if not student:
            return None, [], []

        total_sessions = db.query(Session).count()
        nb_presences = len(student.attendances)
        taux = round((nb_presences / total_sessions) * 100, 1) if total_sessions > 0 else 0

        info = {
            "nom": student.nom,
            "prenom": student.prenom,
            "email": student.email,
            "date_naissance": str(student.date_naissance) if student.date_naissance else "-",
            "taux_presence": taux,
        }

        notes = []
        for g in student.grades:
            notes.append({
                "Cours": g.course.libelle,
                "Code": g.course_code,
                "Note": g.note,
                "Credits": g.course.credits,
            })

        return info, notes, student.grades
    finally:
        db.close()


def get_courses_options(teacher_id=None):
    db = SessionLocal()
    try:
        query = db.query(Course)
        if teacher_id:
            query = query.filter(Course.teacher_id == teacher_id)
        courses = query.all()
        return [{"label": f"{c.code} - {c.libelle}", "value": c.code} for c in courses]
    finally:
        db.close()


# --- Layout ---

def layout():
    return html.Div([
        html.H1("Etudiants & Notes"),

        # Formulaire CRUD etudiant (admin only)
        html.Div([
            html.H3("Gerer les etudiants"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Nom"),
                    dbc.Input(id="input-stu-nom", placeholder="Nom"),
                ], width=3),
                dbc.Col([
                    dbc.Label("Prenom"),
                    dbc.Input(id="input-stu-prenom", placeholder="Prenom"),
                ], width=3),
                dbc.Col([
                    dbc.Label("Email"),
                    dbc.Input(id="input-stu-email", placeholder="email@example.com", type="email"),
                ], width=3),
                dbc.Col([
                    dbc.Label("Date de naissance"),
                    dbc.Input(id="input-stu-dob", type="date"),
                ], width=3),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Button("Ajouter l'etudiant", id="btn-add-student", color="dark", className="me-2"),
                    dbc.Button("Supprimer la selection", id="btn-del-student", color="danger", outline=True),
                ]),
            ]),
            html.Div(id="student-crud-alert", className="mt-2"),
        ], id="student-admin-form", className="mb-4"),

        html.Hr(),

        # Tableau etudiants
        html.H3("Liste des etudiants"),
        html.Div(id="students-table"),

        html.Hr(),

        # Fiche etudiant
        html.H3("Fiche etudiant"),
        html.P("Selectionnez un etudiant dans le tableau ci-dessus.", id="student-hint",
               style={"color": "#73726e"}),
        html.Div(id="student-detail"),

        html.Hr(),

        # Workflow Notes-Excel
        html.H3("Gestion des notes par Excel"),
        dbc.Row([
            dbc.Col([
                html.H5("1. Telecharger le template"),
                dcc.Dropdown(id="template-course", placeholder="Choisir un cours..."),
                dbc.Button("Telecharger le template", id="btn-download-template",
                           color="dark", className="mt-2"),
                dcc.Download(id="download-template"),
            ], width=5),
            dbc.Col([
                html.H5("3. Uploader les notes"),
                dcc.Upload(
                    id="upload-notes",
                    children=html.Div(["Glisser-deposer ou ", html.A("parcourir")]),
                    style={
                        "borderWidth": "1px", "borderStyle": "dashed", "borderColor": "#e8e8e4",
                        "borderRadius": "4px", "textAlign": "center", "padding": "20px",
                        "cursor": "pointer", "backgroundColor": "#fbfbfa",
                    },
                ),
                html.Div(id="upload-alert", className="mt-2"),
            ], width=5),
        ]),
    ])


# --- Callbacks ---

@callback(
    Output("student-admin-form", "style"),
    Input("user-role", "data"),
)
def toggle_student_form(role):
    if role == "admin":
        return {}
    return {"display": "none"}


@callback(
    Output("student-crud-alert", "children"),
    Input("btn-add-student", "n_clicks"),
    Input("btn-del-student", "n_clicks"),
    State("input-stu-nom", "value"),
    State("input-stu-prenom", "value"),
    State("input-stu-email", "value"),
    State("input-stu-dob", "value"),
    State("student-datatable", "selected_rows"),
    State("student-datatable", "data"),
    prevent_initial_call=True,
)
def manage_student(add_clicks, del_clicks, nom, prenom, email, dob, selected_rows, table_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    db = SessionLocal()

    try:
        if trigger == "btn-add-student":
            if not all([nom, prenom, email]):
                return dbc.Alert("Nom, prenom et email sont requis.", color="warning", duration=3000)
            existing = db.query(Student).filter_by(email=email).first()
            if existing:
                return dbc.Alert(f"L'email '{email}' existe deja.", color="danger", duration=3000)
            student = Student(nom=nom, prenom=prenom, email=email, date_naissance=dob)
            db.add(student)
            db.commit()
            return dbc.Alert(f"Etudiant '{prenom} {nom}' ajoute.", color="success", duration=3000)

        elif trigger == "btn-del-student":
            if not selected_rows:
                return dbc.Alert("Selectionnez un etudiant a supprimer.", color="warning", duration=3000)
            student_id = table_data[selected_rows[0]]["ID"]
            student = db.query(Student).filter_by(id=student_id).first()
            if student:
                db.query(Grade).filter_by(student_id=student_id).delete()
                db.query(Attendance).filter_by(student_id=student_id).delete()
                db.delete(student)
                db.commit()
                return dbc.Alert(f"Etudiant supprime.", color="info", duration=3000)
    except Exception as e:
        db.rollback()
        return dbc.Alert(f"Erreur : {e}", color="danger", duration=5000)
    finally:
        db.close()

    return no_update


@callback(
    Output("students-table", "children"),
    Input("upload-alert", "children"),
    Input("student-crud-alert", "children"),
)
def refresh_students(_, __):
    data = get_students_summary()
    if not data:
        return html.P("Aucun etudiant.")

    table_data = [
        {"ID": d["id"], "Nom": d["nom"], "Prenom": d["prenom"],
         "Email": d["email"], "Moyenne": d["moyenne"],
         "Presence": f"{d['taux_presence']}%"}
        for d in data
    ]

    return dash_table.DataTable(
        id="student-datatable",
        data=table_data,
        columns=[{"name": k, "id": k} for k in table_data[0].keys()],
        row_selectable="single",
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#f7f6f3", "fontWeight": "600",
                      "border": "1px solid #e8e8e4"},
        style_cell={"textAlign": "left", "padding": "8px 12px",
                    "border": "1px solid #e8e8e4", "fontSize": "14px"},
        style_data_conditional=[
            {"if": {"filter_query": "{Presence} < 50%"}, "color": "#e74c3c"},
        ],
        page_size=15,
    )


@callback(
    Output("student-detail", "children"),
    Output("student-hint", "style"),
    Input("student-datatable", "selected_rows"),
    State("student-datatable", "data"),
    prevent_initial_call=True,
)
def show_detail(selected_rows, table_data):
    if not selected_rows:
        return no_update, no_update

    student_id = table_data[selected_rows[0]]["ID"]
    info, notes, grades = get_student_detail(student_id)
    if not info:
        return html.P("Etudiant introuvable."), {"display": "none"}

    # Moyenne generale
    if grades:
        total_points = sum(n["Note"] * n["Credits"] for n in notes)
        total_credits = sum(n["Credits"] for n in notes)
        moyenne = round(total_points / total_credits, 2) if total_credits > 0 else 0
    else:
        moyenne = "-"

    # Couleur presence
    color_presence = "#2ecc71" if info["taux_presence"] >= 75 else "#f39c12" if info["taux_presence"] >= 50 else "#e74c3c"

    # Carte info
    card = dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H4(f"{info['prenom']} {info['nom']}"),
                    html.P(f"Email : {info['email']}"),
                    html.P(f"Date de naissance : {info['date_naissance']}"),
                ], width=4),
                dbc.Col([
                    html.H2(str(moyenne), style={"color": "#37352f"}),
                    html.P("Moyenne generale"),
                ], width=4, className="text-center"),
                dbc.Col([
                    html.H2(f"{info['taux_presence']}%", style={"color": color_presence}),
                    html.P("Taux de presence"),
                ], width=4, className="text-center"),
            ]),
        ])
    ], className="mb-3")

    # Graphique notes
    if notes:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[n["Code"] for n in notes],
            y=[n["Note"] for n in notes],
            marker_color=["#2ecc71" if n["Note"] >= 10 else "#e74c3c" for n in notes],
            text=[str(n["Note"]) for n in notes],
            textposition="auto",
        ))
        fig.add_hline(y=10, line_dash="dash", line_color="#73726e", annotation_text="Moyenne")
        fig.update_layout(
            yaxis=dict(range=[0, 20], title="Note"),
            xaxis=dict(title="Cours"),
            height=300,
            margin=dict(l=40, r=20, t=10, b=40),
            template="simple_white",
        )
        chart = dcc.Graph(figure=fig)
    else:
        chart = html.P("Aucune note.")

    # Bouton export PDF
    btn_pdf = html.A(
        dbc.Button("Exporter le bulletin PDF", color="dark", className="mt-3"),
        href=f"/api/bulletin/{student_id}",
        target="_blank",
    )

    return html.Div([card, chart, btn_pdf]), {"display": "none"}


@callback(
    Output("template-course", "options"),
    Input("students-table", "children"),
    Input("user-teacher-id", "data"),
)
def load_template_options(_, teacher_id):
    return get_courses_options(teacher_id)


@callback(
    Output("download-template", "data"),
    Input("btn-download-template", "n_clicks"),
    State("template-course", "value"),
    prevent_initial_call=True,
)
def download_template(n_clicks, course_code):
    if not course_code:
        return no_update

    db = SessionLocal()
    try:
        students = db.query(Student).order_by(Student.nom).all()
        course = db.query(Course).filter_by(code=course_code).first()

        df = pd.DataFrame({
            "ID": [s.id for s in students],
            "Nom": [s.nom for s in students],
            "Prenom": [s.prenom for s in students],
            "Note": ["" for _ in students],
        })

        output = io.BytesIO()
        df.to_excel(output, index=False, sheet_name=course_code)
        output.seek(0)

        return dcc.send_bytes(output.getvalue(), f"notes_{course_code}.xlsx")
    finally:
        db.close()


@callback(
    Output("upload-alert", "children"),
    Input("upload-notes", "contents"),
    State("upload-notes", "filename"),
    prevent_initial_call=True,
)
def upload_notes(contents, filename):
    if not contents or not filename:
        return no_update

    if not filename.endswith(".xlsx"):
        return dbc.Alert("Le fichier doit etre au format .xlsx", color="danger", duration=4000)

    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    try:
        xl = pd.ExcelFile(io.BytesIO(decoded))
        sheet_name = xl.sheet_names[0]
        df = pd.read_excel(xl, sheet_name=sheet_name)

        if "ID" not in df.columns or "Note" not in df.columns:
            return dbc.Alert("Le fichier doit contenir les colonnes 'ID' et 'Note'.",
                             color="danger", duration=4000)

        course_code = sheet_name
        db = SessionLocal()
        try:
            count = 0
            for _, row in df.iterrows():
                if pd.isna(row["Note"]):
                    continue

                student_id = int(row["ID"])
                note = float(row["Note"])

                if note < 0 or note > 20:
                    continue

                existing = db.query(Grade).filter_by(
                    student_id=student_id, course_code=course_code
                ).first()

                if existing:
                    existing.note = note
                else:
                    db.add(Grade(student_id=student_id, course_code=course_code, note=note))
                count += 1

            db.commit()
            return dbc.Alert(f"{count} notes importees pour {course_code}.",
                             color="success", duration=4000)
        except Exception as e:
            db.rollback()
            return dbc.Alert(f"Erreur : {e}", color="danger", duration=5000)
        finally:
            db.close()

    except Exception as e:
        return dbc.Alert(f"Erreur de lecture du fichier : {e}", color="danger", duration=5000)
