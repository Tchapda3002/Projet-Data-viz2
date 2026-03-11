import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update, ALL
import dash_bootstrap_components as dbc
from datetime import date

from database import SessionLocal
from models import Course, Session, Student, Attendance

dash.register_page(__name__, path="/seances", name="Seances & Presences")


def get_courses_options():
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        return [{"label": f"{c.code} - {c.libelle}", "value": c.code} for c in courses]
    finally:
        db.close()


def get_sessions(course_code=None):
    db = SessionLocal()
    try:
        query = db.query(Session)
        if course_code:
            query = query.filter_by(course_code=course_code)
        sessions = query.order_by(Session.date.desc()).all()
        data = []
        for s in sessions:
            nb_presents = len(s.attendances)
            nb_total = db.query(Student).count()
            data.append({
                "ID": s.id,
                "Cours": f"{s.course.code} - {s.course.libelle}",
                "Date": str(s.date),
                "Duree": f"{s.duree}h",
                "Theme": s.theme or "",
                "Presents": f"{nb_presents}/{nb_total}",
            })
        return data
    finally:
        db.close()


def get_students_for_checklist(session_id=None):
    db = SessionLocal()
    try:
        students = db.query(Student).order_by(Student.nom).all()
        present_ids = set()
        if session_id:
            attendances = db.query(Attendance).filter_by(session_id=session_id).all()
            present_ids = {a.student_id for a in attendances}
        return students, present_ids
    finally:
        db.close()


# --- Layout ---

layout = html.Div([
    html.H1("Seances & Presences"),

    # Formulaire nouvelle seance
    html.Div([
        html.H3("Enregistrer une seance"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Cours"),
                dcc.Dropdown(id="seance-course", placeholder="Choisir un cours..."),
            ], width=4),
            dbc.Col([
                dbc.Label("Date"),
                dbc.Input(id="seance-date", type="date", value=str(date.today())),
            ], width=2),
            dbc.Col([
                dbc.Label("Duree (h)"),
                dbc.Input(id="seance-duree", type="number", value=2, min=0.5, step=0.5),
            ], width=2),
            dbc.Col([
                dbc.Label("Theme aborde"),
                dbc.Input(id="seance-theme", placeholder="Theme du cours"),
            ], width=4),
        ], className="mb-3"),

        # Appel numerique
        html.H4("Appel numerique", className="mt-3 mb-2"),
        html.P("Cochez les etudiants presents.", style={"color": "#73726e", "fontSize": "14px"}),
        dbc.Button("Tout cocher", id="btn-check-all", color="secondary", size="sm", className="me-2 mb-2"),
        dbc.Button("Tout decocher", id="btn-uncheck-all", color="secondary", size="sm", outline=True, className="mb-2"),
        html.Div(id="checklist-container"),

        dbc.Button("Enregistrer la seance", id="btn-save-seance", color="dark", className="mt-3"),
        html.Div(id="seance-alert", className="mt-2"),
    ], className="mb-4"),

    html.Hr(),

    # Historique des seances
    html.H3("Historique des seances"),
    dbc.Row([
        dbc.Col([
            dcc.Dropdown(id="filter-course", placeholder="Filtrer par cours...", clearable=True),
        ], width=4),
    ], className="mb-3"),
    html.Div(id="sessions-table"),
])


# --- Callbacks ---

@callback(
    Output("seance-course", "options"),
    Output("filter-course", "options"),
    Input("seance-alert", "children"),
)
def load_course_options(_):
    options = get_courses_options()
    return options, options


@callback(
    Output("checklist-container", "children"),
    Input("seance-course", "value"),
)
def show_checklist(course_code):
    if not course_code:
        return html.P("Selectionnez un cours pour afficher la liste.", style={"color": "#73726e"})

    students, _ = get_students_for_checklist()
    if not students:
        return html.P("Aucun etudiant.")

    checklist = dbc.Checklist(
        id="attendance-checklist",
        options=[{"label": f"  {s.nom} {s.prenom}", "value": s.id} for s in students],
        value=[s.id for s in students],  # tous presents par defaut
        style={"columnCount": 3},
    )
    return checklist


@callback(
    Output("attendance-checklist", "value"),
    Input("btn-check-all", "n_clicks"),
    Input("btn-uncheck-all", "n_clicks"),
    State("attendance-checklist", "options"),
    prevent_initial_call=True,
)
def toggle_all(check, uncheck, options):
    ctx = dash.callback_context
    if not ctx.triggered or not options:
        return no_update
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "btn-check-all":
        return [o["value"] for o in options]
    return []


@callback(
    Output("seance-alert", "children"),
    Input("btn-save-seance", "n_clicks"),
    State("seance-course", "value"),
    State("seance-date", "value"),
    State("seance-duree", "value"),
    State("seance-theme", "value"),
    State("attendance-checklist", "value"),
    prevent_initial_call=True,
)
def save_seance(n_clicks, course_code, seance_date, duree, theme, present_ids):
    if not all([course_code, seance_date, duree]):
        return dbc.Alert("Cours, date et duree sont requis.", color="warning", duration=3000)

    db = SessionLocal()
    try:
        session = Session(
            course_code=course_code,
            date=seance_date,
            duree=float(duree),
            theme=theme,
        )
        db.add(session)
        db.flush()

        if present_ids:
            for student_id in present_ids:
                db.add(Attendance(session_id=session.id, student_id=student_id))

        db.commit()

        nb_presents = len(present_ids) if present_ids else 0
        nb_total = db.query(Student).count()
        return dbc.Alert(
            f"Seance enregistree. Presents : {nb_presents}/{nb_total}",
            color="success", duration=4000,
        )
    except Exception as e:
        db.rollback()
        return dbc.Alert(f"Erreur : {e}", color="danger", duration=5000)
    finally:
        db.close()


@callback(
    Output("sessions-table", "children"),
    Input("filter-course", "value"),
    Input("seance-alert", "children"),
)
def refresh_sessions(course_filter, _):
    data = get_sessions(course_filter)
    if not data:
        return html.P("Aucune seance enregistree.")

    return dash_table.DataTable(
        data=data,
        columns=[{"name": k, "id": k} for k in data[0].keys() if k != "ID"],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#f7f6f3", "fontWeight": "600",
                      "border": "1px solid #e8e8e4"},
        style_cell={"textAlign": "left", "padding": "8px 12px",
                    "border": "1px solid #e8e8e4", "fontSize": "14px"},
        page_size=15,
    )
