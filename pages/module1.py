import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from database import SessionLocal
from models import Course, Session, Teacher

dash.register_page(__name__, path="/cours", name="Cours")


def get_courses():
    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        data = []
        for c in courses:
            heures_effectuees = sum(s.duree for s in c.sessions)
            progression = round((heures_effectuees / c.volume_horaire) * 100, 1) if c.volume_horaire > 0 else 0
            data.append({
                "code": c.code,
                "libelle": c.libelle,
                "volume_horaire": c.volume_horaire,
                "heures_effectuees": heures_effectuees,
                "progression": progression,
                "credits": c.credits,
                "enseignant": f"{c.teacher.prenom} {c.teacher.nom}",
                "teacher_id": c.teacher_id,
            })
        return data
    finally:
        db.close()


def get_teachers_options():
    db = SessionLocal()
    try:
        teachers = db.query(Teacher).all()
        return [{"label": f"{t.prenom} {t.nom}", "value": t.id} for t in teachers]
    finally:
        db.close()


# --- Layout ---

layout = html.Div([
    html.H1("Gestion des Cours"),

    # Formulaire ajout
    html.Div([
        html.H3("Ajouter un cours"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Code"),
                dbc.Input(id="input-code", placeholder="ex: MATH101"),
            ], width=3),
            dbc.Col([
                dbc.Label("Libelle"),
                dbc.Input(id="input-libelle", placeholder="Nom du cours"),
            ], width=4),
            dbc.Col([
                dbc.Label("Volume horaire"),
                dbc.Input(id="input-volume", type="number", placeholder="20"),
            ], width=2),
            dbc.Col([
                dbc.Label("Credits"),
                dbc.Input(id="input-credits", type="number", placeholder="1.5"),
            ], width=1),
            dbc.Col([
                dbc.Label("Enseignant"),
                dcc.Dropdown(id="input-teacher", placeholder="Choisir..."),
            ], width=2),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Ajouter", id="btn-add-course", color="dark", className="me-2"),
                dbc.Button("Supprimer la selection", id="btn-del-course", color="danger", outline=True),
            ]),
        ]),
        html.Div(id="course-alert", className="mt-2"),
    ], className="mb-4"),

    html.Hr(),

    # Tableau des cours
    html.H3("Liste des cours"),
    html.Div(id="courses-table"),

    html.Hr(),

    # Barres de progression
    html.H3("Progression des cours"),
    dcc.Graph(id="progress-chart"),
])


# --- Callbacks ---

@callback(
    Output("input-teacher", "options"),
    Input("courses-table", "children"),
)
def load_teachers(_):
    return get_teachers_options()


@callback(
    Output("courses-table", "children"),
    Output("progress-chart", "figure"),
    Input("course-alert", "children"),
)
def refresh_courses(_):
    data = get_courses()
    if not data:
        empty_fig = go.Figure()
        empty_fig.update_layout(template="simple_white")
        return html.P("Aucun cours."), empty_fig

    table_data = [
        {"Code": d["code"], "Libelle": d["libelle"], "Volume H.": d["volume_horaire"],
         "Effectuees": d["heures_effectuees"], "Progression": f"{d['progression']}%",
         "Credits": d["credits"], "Enseignant": d["enseignant"]}
        for d in data
    ]

    table = dash_table.DataTable(
        id="course-datatable",
        data=table_data,
        columns=[{"name": k, "id": k} for k in table_data[0].keys()],
        row_selectable="single",
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#f7f6f3", "fontWeight": "600",
                      "border": "1px solid #e8e8e4"},
        style_cell={"textAlign": "left", "padding": "8px 12px",
                    "border": "1px solid #e8e8e4", "fontSize": "14px"},
        page_size=15,
    )

    # Graphique de progression
    fig = go.Figure()
    sorted_data = sorted(data, key=lambda x: x["progression"])
    fig.add_trace(go.Bar(
        x=[d["progression"] for d in sorted_data],
        y=[d["libelle"][:35] for d in sorted_data],
        orientation="h",
        marker_color=["#2ecc71" if d["progression"] >= 75
                       else "#f39c12" if d["progression"] >= 40
                       else "#e74c3c" for d in sorted_data],
        text=[f"{d['progression']}%" for d in sorted_data],
        textposition="auto",
    ))

    fig.update_layout(
        xaxis=dict(range=[0, 100], title="Progression (%)"),
        height=max(400, len(data) * 30),
        margin=dict(l=250, r=20, t=10, b=40),
        template="simple_white",
        showlegend=False,
    )

    return table, fig


@callback(
    Output("course-alert", "children"),
    Input("btn-add-course", "n_clicks"),
    Input("btn-del-course", "n_clicks"),
    State("input-code", "value"),
    State("input-libelle", "value"),
    State("input-volume", "value"),
    State("input-credits", "value"),
    State("input-teacher", "value"),
    State("course-datatable", "selected_rows"),
    State("course-datatable", "data"),
    prevent_initial_call=True,
)
def manage_course(add_clicks, del_clicks, code, libelle, volume, credits, teacher_id,
                  selected_rows, table_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    db = SessionLocal()

    try:
        if trigger == "btn-add-course":
            if not all([code, libelle, volume, credits, teacher_id]):
                return dbc.Alert("Tous les champs sont requis.", color="warning", duration=3000)

            existing = db.query(Course).filter_by(code=code).first()
            if existing:
                return dbc.Alert(f"Le code '{code}' existe deja.", color="danger", duration=3000)

            db.add(Course(code=code, libelle=libelle, volume_horaire=float(volume),
                          credits=float(credits), teacher_id=int(teacher_id)))
            db.commit()
            return dbc.Alert(f"Cours '{libelle}' ajoute.", color="success", duration=3000)

        elif trigger == "btn-del-course":
            if not selected_rows:
                return dbc.Alert("Selectionnez un cours a supprimer.", color="warning", duration=3000)

            code_to_del = table_data[selected_rows[0]]["Code"]
            course = db.query(Course).filter_by(code=code_to_del).first()
            if course:
                for session in course.sessions:
                    for att in session.attendances:
                        db.delete(att)
                    db.delete(session)
                for grade in course.grades:
                    db.delete(grade)
                db.delete(course)
                db.commit()
                return dbc.Alert(f"Cours '{code_to_del}' supprime.", color="info", duration=3000)

    except Exception as e:
        db.rollback()
        return dbc.Alert(f"Erreur : {e}", color="danger", duration=5000)
    finally:
        db.close()

    return no_update
