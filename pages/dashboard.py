import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import date

from database import SessionLocal
from models import Student, Course, Session, Attendance, Grade, Teacher

dash.register_page(__name__, path="/", name="Tableau de bord")


def get_dashboard_data(course_filter=None, teacher_id=None):
    db = SessionLocal()
    try:
        # Filtrage
        courses_query = db.query(Course)
        if teacher_id:
            courses_query = courses_query.filter(Course.teacher_id == teacher_id)
        if course_filter:
            courses_query = courses_query.filter(Course.code == course_filter)
        courses = courses_query.all()
        course_codes = [c.code for c in courses]

        students = db.query(Student).all()
        all_sessions = db.query(Session).filter(Session.course_code.in_(course_codes)).all() if course_codes else []
        all_grades = db.query(Grade).filter(Grade.course_code.in_(course_codes)).all() if course_codes else []
        all_attendance = []
        session_ids = [s.id for s in all_sessions]
        if session_ids:
            all_attendance = db.query(Attendance).filter(Attendance.session_id.in_(session_ids)).all()

        # KPIs
        nb_students = len(students)
        nb_courses = len(courses)
        nb_sessions = len(all_sessions)
        nb_teachers = db.query(Teacher).count()

        # Moyenne generale
        if all_grades:
            total_points = sum(g.note for g in all_grades)
            moyenne_gen = round(total_points / len(all_grades), 2)
        else:
            moyenne_gen = 0

        # Taux de presence global
        if all_sessions and students:
            total_possible = len(all_sessions) * nb_students
            total_presents = len(all_attendance)
            taux_presence = round((total_presents / total_possible) * 100, 1) if total_possible > 0 else 0
        else:
            taux_presence = 0

        # Taux de reussite (note >= 10)
        if all_grades:
            nb_reussite = sum(1 for g in all_grades if g.note >= 10)
            taux_reussite = round((nb_reussite / len(all_grades)) * 100, 1)
        else:
            taux_reussite = 0

        # Distribution des notes
        notes = [g.note for g in all_grades]

        # Moyennes par cours
        moyennes_cours = []
        for c in courses:
            grades_cours = [g.note for g in all_grades if g.course_code == c.code]
            if grades_cours:
                moy = round(sum(grades_cours) / len(grades_cours), 2)
                moyennes_cours.append({"cours": c.libelle[:25], "code": c.code, "moyenne": moy})

        # Progression des cours
        progression_cours = []
        for c in courses:
            heures = sum(s.duree for s in all_sessions if s.course_code == c.code)
            pct = round((heures / c.volume_horaire) * 100, 1) if c.volume_horaire > 0 else 0
            progression_cours.append({"cours": c.libelle[:25], "code": c.code,
                                      "heures": heures, "total": c.volume_horaire, "pct": pct})

        # Presence par cours
        presence_cours = []
        for c in courses:
            sessions_c = [s for s in all_sessions if s.course_code == c.code]
            s_ids = [s.id for s in sessions_c]
            att_c = [a for a in all_attendance if a.session_id in s_ids]
            total_p = len(sessions_c) * nb_students if sessions_c else 0
            pct_p = round((len(att_c) / total_p) * 100, 1) if total_p > 0 else 0
            presence_cours.append({"cours": c.libelle[:25], "code": c.code, "pct": pct_p})

        # Top/bottom etudiants (notes)
        etudiants_perf = []
        for s in students:
            grades_s = [g for g in all_grades if g.student_id == s.id]
            if grades_s:
                moy = round(sum(g.note for g in grades_s) / len(grades_s), 2)
                etudiants_perf.append({"nom": f"{s.prenom} {s.nom}", "moyenne": moy})
        etudiants_perf.sort(key=lambda x: x["moyenne"], reverse=True)

        # Top/bottom etudiants (assiduite)
        etudiants_assiduite = []
        if all_sessions:
            for s in students:
                presences_s = sum(1 for a in all_attendance if a.student_id == s.id)
                taux = round((presences_s / len(all_sessions)) * 100, 1)
                etudiants_assiduite.append({"nom": f"{s.prenom} {s.nom}", "taux": taux})
            etudiants_assiduite.sort(key=lambda x: x["taux"], reverse=True)

        return {
            "nb_students": nb_students,
            "nb_courses": nb_courses,
            "nb_sessions": nb_sessions,
            "nb_teachers": nb_teachers,
            "moyenne_gen": moyenne_gen,
            "taux_presence": taux_presence,
            "taux_reussite": taux_reussite,
            "notes": notes,
            "moyennes_cours": moyennes_cours,
            "progression_cours": progression_cours,
            "presence_cours": presence_cours,
            "top_students": etudiants_perf[:5],
            "bottom_students": etudiants_perf[-5:] if len(etudiants_perf) >= 5 else etudiants_perf,
            "top_assidus": etudiants_assiduite[:5],
            "bottom_assidus": etudiants_assiduite[-5:] if len(etudiants_assiduite) >= 5 else etudiants_assiduite,
        }
    except Exception:
        return None
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


def make_kpi_card(value, label, color="var(--text-primary)"):
    return dbc.Col(
        html.Div([
            html.Div(str(value), className="kpi-value", style={"color": color}),
            html.Div(label, className="kpi-label"),
        ], className="kpi-card"),
        xs=6, sm=4, md=3, lg=True,
    )


# --- Layout ---

layout = html.Div([
    html.Div([
        html.H1("Tableau de bord"),
        html.P("Vue d'ensemble de la situation academique."),
    ], className="page-header"),

    # Filtres
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Div("FILTRER PAR COURS", className="filter-label"),
                dcc.Dropdown(id="dash-filter-course", placeholder="Tous les cours",
                             clearable=True),
            ], width=4),
        ]),
    ], className="filters-bar"),

    # KPIs
    html.Div(id="kpi-row"),

    # Graphiques ligne 1
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div("Distribution des notes", className="chart-title"),
                dcc.Graph(id="chart-notes-dist", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], md=6),
        dbc.Col([
            html.Div([
                html.Div("Moyenne par cours", className="chart-title"),
                dcc.Graph(id="chart-moyennes", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], md=6),
    ], className="mb-4"),

    # Graphiques ligne 2
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div("Progression des cours", className="chart-title"),
                dcc.Graph(id="chart-progression", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], md=6),
        dbc.Col([
            html.Div([
                html.Div("Taux de presence par cours", className="chart-title"),
                dcc.Graph(id="chart-presence", config={"displayModeBar": False}),
            ], className="chart-card"),
        ], md=6),
    ], className="mb-4"),

    # Top / Bottom etudiants
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div("Top 5 etudiants", className="chart-title"),
                html.Div(id="top-students"),
            ], className="chart-card"),
        ], md=6),
        dbc.Col([
            html.Div([
                html.Div("5 etudiants en difficulte", className="chart-title"),
                html.Div(id="bottom-students"),
            ], className="chart-card"),
        ], md=6),
    ], className="mb-4"),

    # Assiduite
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div("Meilleure assiduite", className="chart-title"),
                html.Div(id="top-assidus"),
            ], className="chart-card"),
        ], md=6),
        dbc.Col([
            html.Div([
                html.Div("Assiduite a surveiller", className="chart-title"),
                html.Div(id="bottom-assidus"),
            ], className="chart-card"),
        ], md=6),
    ]),
])


# --- Callbacks ---

@callback(
    Output("dash-filter-course", "options"),
    Input("dash-filter-course", "value"),
    Input("user-teacher-id", "data"),
)
def load_options(_, teacher_id):
    return get_courses_options(teacher_id)


@callback(
    Output("kpi-row", "children"),
    Output("chart-notes-dist", "figure"),
    Output("chart-moyennes", "figure"),
    Output("chart-progression", "figure"),
    Output("chart-presence", "figure"),
    Output("top-students", "children"),
    Output("bottom-students", "children"),
    Output("top-assidus", "children"),
    Output("bottom-assidus", "children"),
    Input("dash-filter-course", "value"),
    Input("user-teacher-id", "data"),
)
def update_dashboard(course_filter, teacher_id):
    data = get_dashboard_data(course_filter, teacher_id)

    empty_fig = go.Figure()
    empty_fig.update_layout(template="simple_white", height=300,
                            margin=dict(l=20, r=20, t=10, b=20))

    if not data:
        kpis = html.P("Aucune donnee. Allez dans Initialisation pour importer les donnees.")
        return kpis, empty_fig, empty_fig, empty_fig, empty_fig, "", "", "", ""

    # KPIs
    kpis = dbc.Row([
        make_kpi_card(data["nb_students"], "Etudiants"),
        make_kpi_card(data["nb_courses"], "Cours"),
        make_kpi_card(data["nb_sessions"], "Seances"),
        make_kpi_card(data["nb_teachers"], "Enseignants"),
        make_kpi_card(f"{data['moyenne_gen']}/20", "Moyenne generale",
                      "#2ecc71" if data["moyenne_gen"] >= 10 else "#e74c3c"),
        make_kpi_card(f"{data['taux_presence']}%", "Presence",
                      "#2ecc71" if data["taux_presence"] >= 75 else "#f39c12"),
        make_kpi_card(f"{data['taux_reussite']}%", "Reussite",
                      "#2ecc71" if data["taux_reussite"] >= 50 else "#e74c3c"),
    ], className="kpi-row")

    # Distribution des notes
    if data["notes"]:
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=data["notes"], nbinsx=20,
            marker_color="rgba(35, 131, 226, 0.7)",
            marker_line=dict(color="rgba(35, 131, 226, 1)", width=1),
        ))
        fig_dist.add_vline(x=10, line_dash="dash", line_color="#73726e",
                           annotation_text="Moy. 10")
        fig_dist.update_layout(
            xaxis=dict(title="Note", range=[0, 20]),
            yaxis=dict(title="Nombre"),
            height=300, margin=dict(l=40, r=20, t=10, b=40),
            template="simple_white", bargap=0.05,
        )
    else:
        fig_dist = empty_fig

    # Moyennes par cours
    if data["moyennes_cours"]:
        sorted_moy = sorted(data["moyennes_cours"], key=lambda x: x["moyenne"])
        fig_moy = go.Figure()
        fig_moy.add_trace(go.Bar(
            x=[m["moyenne"] for m in sorted_moy],
            y=[m["cours"] for m in sorted_moy],
            orientation="h",
            marker_color=["#2ecc71" if m["moyenne"] >= 10 else "#e74c3c" for m in sorted_moy],
            text=[str(m["moyenne"]) for m in sorted_moy],
            textposition="auto",
        ))
        fig_moy.add_vline(x=10, line_dash="dash", line_color="#73726e")
        fig_moy.update_layout(
            xaxis=dict(range=[0, 20], title="Moyenne"),
            height=max(250, len(sorted_moy) * 28),
            margin=dict(l=180, r=20, t=10, b=40),
            template="simple_white", showlegend=False,
        )
    else:
        fig_moy = empty_fig

    # Progression des cours
    if data["progression_cours"]:
        sorted_prog = sorted(data["progression_cours"], key=lambda x: x["pct"])
        fig_prog = go.Figure()
        fig_prog.add_trace(go.Bar(
            x=[p["pct"] for p in sorted_prog],
            y=[p["cours"] for p in sorted_prog],
            orientation="h",
            marker_color=["#2ecc71" if p["pct"] >= 75
                          else "#f39c12" if p["pct"] >= 40
                          else "#e74c3c" for p in sorted_prog],
            text=[f"{p['pct']}%" for p in sorted_prog],
            textposition="auto",
        ))
        fig_prog.update_layout(
            xaxis=dict(range=[0, 100], title="Progression (%)"),
            height=max(250, len(sorted_prog) * 28),
            margin=dict(l=180, r=20, t=10, b=40),
            template="simple_white", showlegend=False,
        )
    else:
        fig_prog = empty_fig

    # Presence par cours
    if data["presence_cours"]:
        sorted_pres = sorted(data["presence_cours"], key=lambda x: x["pct"])
        fig_pres = go.Figure()
        fig_pres.add_trace(go.Bar(
            x=[p["pct"] for p in sorted_pres],
            y=[p["cours"] for p in sorted_pres],
            orientation="h",
            marker_color=["#2ecc71" if p["pct"] >= 80
                          else "#f39c12" if p["pct"] >= 60
                          else "#e74c3c" for p in sorted_pres],
            text=[f"{p['pct']}%" for p in sorted_pres],
            textposition="auto",
        ))
        fig_pres.update_layout(
            xaxis=dict(range=[0, 100], title="Presence (%)"),
            height=max(250, len(sorted_pres) * 28),
            margin=dict(l=180, r=20, t=10, b=40),
            template="simple_white", showlegend=False,
        )
    else:
        fig_pres = empty_fig

    # Top students (notes)
    def student_list(students_data, color, value_key="moyenne", suffix="/20"):
        if not students_data:
            return html.P("Aucune donnee.", style={"color": "var(--text-tertiary)"})
        items = []
        for i, s in enumerate(students_data):
            items.append(html.Div([
                html.Span(f"{i+1}.", className="rank-num"),
                html.Span(s["nom"], className="rank-name"),
                html.Span(f"{s[value_key]}{suffix}", className="rank-score",
                           style={"color": color}),
            ], className="rank-item"))
        return html.Div(items)

    top = student_list(data["top_students"], "#2ecc71")
    bottom = student_list(data["bottom_students"], "#e74c3c")

    # Assiduite
    top_assidus = student_list(data["top_assidus"], "#2ecc71", "taux", "%")
    bottom_assidus = student_list(data["bottom_assidus"], "#e74c3c", "taux", "%")

    return kpis, fig_dist, fig_moy, fig_prog, fig_pres, top, bottom, top_assidus, bottom_assidus
