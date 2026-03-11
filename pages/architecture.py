import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

dash.register_page(__name__, path="/architecture", name="Architecture")


def create_flux_diagram():
    """Schema du flux : Navigateur -> Dash -> API Flask -> SQLAlchemy -> PostgreSQL."""
    fig = go.Figure()

    # Boites
    boxes = [
        {"x": 0.5, "y": 0.85, "text": "Navigateur<br>(Utilisateur)", "color": "#f7f6f3"},
        {"x": 0.5, "y": 0.65, "text": "Dash<br>(Frontend)", "color": "#e3f2fd"},
        {"x": 0.5, "y": 0.45, "text": "Flask / API<br>(Backend)", "color": "#fff3e0"},
        {"x": 0.5, "y": 0.25, "text": "SQLAlchemy<br>(ORM)", "color": "#f3e5f5"},
        {"x": 0.5, "y": 0.05, "text": "PostgreSQL<br>(Supabase)", "color": "#e8f5e9"},
    ]

    for box in boxes:
        fig.add_shape(
            type="rect",
            x0=box["x"] - 0.15, y0=box["y"] - 0.06,
            x1=box["x"] + 0.15, y1=box["y"] + 0.06,
            fillcolor=box["color"], line=dict(color="#37352f", width=1),
        )
        fig.add_annotation(
            x=box["x"], y=box["y"], text=box["text"],
            showarrow=False, font=dict(size=13, color="#37352f"),
        )

    # Fleches
    arrows = [
        {"x": 0.5, "y": 0.79, "ay": 0.71, "text": "HTTP Request"},
        {"x": 0.5, "y": 0.59, "ay": 0.51, "text": "Callback"},
        {"x": 0.5, "y": 0.39, "ay": 0.31, "text": "Query ORM"},
        {"x": 0.5, "y": 0.19, "ay": 0.11, "text": "SQL"},
    ]

    for a in arrows:
        fig.add_annotation(
            x=a["x"], y=a["ay"], ax=a["x"], ay=a["y"],
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.5, arrowcolor="#73726e",
        )
        fig.add_annotation(
            x=a["x"] + 0.17, y=(a["y"] + a["ay"]) / 2, text=a["text"],
            showarrow=False, font=dict(size=11, color="#73726e"),
        )

    fig.update_layout(
        xaxis=dict(range=[0, 1], visible=False),
        yaxis=dict(range=[-0.05, 0.95], visible=False),
        height=500, margin=dict(l=20, r=20, t=20, b=20),
        template="simple_white", plot_bgcolor="white",
    )
    return fig


def create_db_schema():
    """Schema relationnel de la base de donnees avec cardinalites."""
    fig = go.Figure()

    # Position des tables
    tables = {
        "Users":      {"x": 0.1, "y": 0.85, "cols": "id, email, password_hash\nrole, nom, prenom"},
        "Teachers":   {"x": 0.1, "y": 0.45, "cols": "id, nom, prenom\nemail, telephone"},
        "Students":   {"x": 0.5, "y": 0.85, "cols": "id, nom, prenom\nemail, date_naissance"},
        "Courses":    {"x": 0.5, "y": 0.45, "cols": "code (PK), libelle\nvolume_horaire, credits\nteacher_id (FK)"},
        "Sessions":   {"x": 0.9, "y": 0.45, "cols": "id, course_code (FK)\ndate, duree, theme"},
        "Attendance": {"x": 0.9, "y": 0.85, "cols": "id, session_id (FK)\nstudent_id (FK)"},
        "Grades":     {"x": 0.5, "y": 0.1,  "cols": "id, student_id (FK)\ncourse_code (FK), note"},
    }

    for name, t in tables.items():
        # Table box
        fig.add_shape(
            type="rect",
            x0=t["x"] - 0.12, y0=t["y"] - 0.1,
            x1=t["x"] + 0.12, y1=t["y"] + 0.1,
            fillcolor="#f7f6f3", line=dict(color="#37352f", width=1),
        )
        # Titre
        fig.add_annotation(
            x=t["x"], y=t["y"] + 0.06,
            text=f"<b>{name}</b>", showarrow=False,
            font=dict(size=13, color="#37352f"),
        )
        # Colonnes
        fig.add_annotation(
            x=t["x"], y=t["y"] - 0.02,
            text=t["cols"], showarrow=False,
            font=dict(size=10, color="#73726e"), align="center",
        )

    # Relations avec cardinalites
    relations = [
        # Teachers 1 --> N Courses
        {"x0": 0.22, "y0": 0.45, "x1": 0.38, "y1": 0.45, "label": "1 → N"},
        # Courses 1 --> N Sessions
        {"x0": 0.62, "y0": 0.45, "x1": 0.78, "y1": 0.45, "label": "1 → N"},
        # Sessions 1 --> N Attendance
        {"x0": 0.9, "y0": 0.55, "x1": 0.9, "y1": 0.75, "label": "1 → N"},
        # Students 1 --> N Attendance
        {"x0": 0.62, "y0": 0.85, "x1": 0.78, "y1": 0.85, "label": "1 → N"},
        # Students 1 --> N Grades
        {"x0": 0.5, "y0": 0.75, "x1": 0.5, "y1": 0.2, "label": "1 → N"},
        # Courses 1 --> N Grades
        {"x0": 0.5, "y0": 0.35, "x1": 0.5, "y1": 0.2, "label": "1 → N"},
    ]

    for r in relations:
        fig.add_annotation(
            x=r["x1"], y=r["y1"], ax=r["x0"], ay=r["y0"],
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor="#73726e",
        )
        mid_x = (r["x0"] + r["x1"]) / 2
        mid_y = (r["y0"] + r["y1"]) / 2
        fig.add_annotation(
            x=mid_x + 0.04, y=mid_y + 0.03,
            text=r["label"], showarrow=False,
            font=dict(size=10, color="#f39c12"),
        )

    fig.update_layout(
        xaxis=dict(range=[-0.05, 1.05], visible=False),
        yaxis=dict(range=[-0.05, 1.0], visible=False),
        height=600, margin=dict(l=20, r=20, t=20, b=20),
        template="simple_white", plot_bgcolor="white",
    )
    return fig


# --- Layout ---

layout = html.Div([
    html.H1("Architecture"),

    html.H3("Flux de l'application"),
    html.P("Comment le trafic circule entre le navigateur et la base de donnees."),
    dcc.Graph(figure=create_flux_diagram()),

    html.Hr(),

    html.H3("Schema de la base de donnees"),
    html.P("Tables, relations et cardinalites."),
    dcc.Graph(figure=create_db_schema()),
])
