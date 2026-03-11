import os
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from flask import session as flask_session
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
server.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

# Enregistrement des routes API REST
from api import register_api
register_api(server)

# Route PDF bulletin
from pdf_export import register_pdf_routes
register_pdf_routes(server)

# Navigation par role
nav_admin = [
    {"icon": "\u25C9", "label": "Tableau de bord", "href": "/"},
    {"icon": "\u25A3", "label": "Cours", "href": "/cours"},
    {"icon": "\u2637", "label": "Seances & Presences", "href": "/seances"},
    {"icon": "\u263B", "label": "Etudiants & Notes", "href": "/etudiants"},
    {"icon": "\u2699", "label": "Administration", "href": "/admin"},
    {"icon": "\u2B21", "label": "Architecture", "href": "/architecture"},
]

nav_enseignant = [
    {"icon": "\u25C9", "label": "Tableau de bord", "href": "/"},
    {"icon": "\u25A3", "label": "Mes Cours", "href": "/cours"},
    {"icon": "\u2637", "label": "Mes Seances", "href": "/seances"},
    {"icon": "\u263B", "label": "Etudiants & Notes", "href": "/etudiants"},
]

# Tous les liens possibles (pour les IDs de callback)
all_nav_items = nav_admin


def make_sidebar_link(icon, label, href):
    link_id = href.strip("/") or "home"
    return dcc.Link(
        html.Div([
            html.Span(icon, className="nav-icon"),
            html.Span(label),
        ], className="nav-item-inner"),
        href=href,
        className="nav-item",
        id=f"nav-{link_id}",
    )


# Protection des routes : redirection vers /login si non connecte
from flask import redirect, request
import bcrypt
from database import SessionLocal
from models import User

@server.before_request
def require_login():
    allowed = ["/login", "/logout", "/auth/login", "/_dash", "/assets", "/_reload-hash", "/_favicon.ico"]
    path = request.path
    if any(path.startswith(a) for a in allowed):
        return
    if not flask_session.get("user_id"):
        return redirect("/login")
    # Protection page admin
    if path == "/admin" and flask_session.get("user_role") != "admin":
        return redirect("/")


# Route de login (formulaire POST classique)
@server.route("/auth/login", methods=["POST"])
def auth_login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return redirect("/login")

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return redirect("/login")

        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return redirect("/login")

        flask_session["user_id"] = user.id
        flask_session["user_email"] = user.email
        flask_session["user_role"] = user.role
        flask_session["user_nom"] = f"{user.prenom} {user.nom}"
        flask_session["teacher_id"] = user.teacher_id

        return redirect("/")
    finally:
        db.close()


# Route de deconnexion
@server.route("/logout")
def logout():
    flask_session.clear()
    return redirect("/login")


def serve_layout():
    """Layout dynamique : login ou app complet selon la session."""
    logged_in = flask_session.get("user_id") is not None

    if not logged_in:
        return html.Div([
            dcc.Location(id="url", refresh=True),
            dcc.Store(id="user-role", data=None),
            dcc.Store(id="user-teacher-id", data=None),
            dash.page_container,
        ])

    user_name = flask_session.get("user_nom", "Utilisateur")
    user_role = flask_session.get("user_role", "admin")
    nav_items = nav_admin if user_role == "admin" else nav_enseignant
    role_label = "Administrateur" if user_role == "admin" else "Enseignant"

    return html.Div([
        dcc.Location(id="url", refresh=False),
        # Store le role et teacher_id pour les callbacks des pages
        dcc.Store(id="user-role", data=user_role),
        dcc.Store(id="user-teacher-id", data=flask_session.get("teacher_id")),
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
                        html.Span("PostgreSQL Railway", className="status-text"),
                    ], className="status-bar"),
                    html.Div([
                        html.Div([
                            html.Span(user_name, style={"fontSize": "12px", "color": "#73726e", "display": "block"}),
                            html.Span(role_label, className="role-badge"),
                        ]),
                        html.A("Deconnexion", href="/logout", className="logout-link"),
                    ], className="user-bar"),
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


app.layout = serve_layout

# Callback pour marquer l'onglet actif dans la sidebar
nav_ids = [f"nav-{item['href'].strip('/') or 'home'}" for item in all_nav_items]
nav_hrefs = [item["href"] for item in all_nav_items]


@callback(
    [Output(nid, "className") for nid in nav_ids],
    Input("url", "pathname"),
)
def update_active_nav(pathname):
    if not pathname or pathname == "/login":
        return ["nav-item"] * len(nav_ids)
    classes = []
    for href in nav_hrefs:
        if pathname == href or (href != "/" and pathname and pathname.startswith(href)):
            classes.append("nav-item active")
        else:
            classes.append("nav-item")
    return classes


if __name__ == "__main__":
    app.run(debug=True)
