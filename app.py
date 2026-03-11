import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from database import engine, Base

# Creation des tables si elles n'existent pas
import models
try:
    Base.metadata.create_all(bind=engine)
    print("Connexion a la base de donnees reussie.")
except Exception as e:
    print(f"Erreur de connexion a la base: {e}")
    print("L'application demarre sans base de donnees.")

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap",
    ],
    suppress_callback_exceptions=True,
)
server = app.server

# Enregistrement des routes API REST
from api import register_api
register_api(server)

# Navigation avec icones unicode
nav_items = [
    {"icon": "\u25C9", "label": "Tableau de bord", "href": "/"},
    {"icon": "\u25A3", "label": "Cours", "href": "/cours"},
    {"icon": "\u2637", "label": "Seances & Presences", "href": "/seances"},
    {"icon": "\u263B", "label": "Etudiants & Notes", "href": "/etudiants"},
    {"icon": "\u2B21", "label": "Architecture", "href": "/architecture"},
    {"icon": "\u2699", "label": "Initialisation", "href": "/init"},
]


def make_sidebar_link(icon, label, href):
    return dcc.Link(
        html.Div([
            html.Span(icon, className="nav-icon"),
            html.Span(label),
        ], className="nav-item-inner"),
        href=href,
        className="nav-item",
    )


app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div([
        # Sidebar
        html.Aside([
            # Brand
            html.Div([
                html.Div("S", className="brand-icon-wrap"),
                html.Div([
                    html.H1("SGA", className="brand-title"),
                    html.Span("Gestion Academique", className="brand-subtitle"),
                ], className="brand-text"),
            ], className="brand"),

            html.Div(className="sidebar-divider"),

            # Navigation
            html.Nav([
                html.Div("MENU", className="nav-section-label"),
                *[make_sidebar_link(item["icon"], item["label"], item["href"])
                  for item in nav_items],
            ], className="nav-section"),

            # Footer
            html.Div([
                html.Div(className="sidebar-divider"),
                html.Div([
                    html.Div(className="status-dot"),
                    html.Span("PostgreSQL connecte", className="status-text"),
                ], className="status-bar"),
            ], className="sidebar-footer"),
        ], className="sidebar-container"),

        # Main content
        html.Main([
            html.Div([
                dash.page_container,
            ], className="page-inner"),
        ], className="content"),
    ], className="app-container"),
])

if __name__ == "__main__":
    app.run(debug=True)
