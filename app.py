import os
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from flask import session as flask_session
from database import engine, Base

# Creation des tables si elles n'existent pas
import models
import bcrypt
from sqlalchemy import text
from database import SessionLocal
from models import User
try:
    Base.metadata.create_all(bind=engine)
    # Migration : ajouter teacher_id a users si manquant
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN teacher_id INTEGER REFERENCES teachers(id)"))
            conn.commit()
            print("Migration: colonne teacher_id ajoutee a users.")
        except Exception:
            conn.rollback()  # colonne existe deja
    # Creer le compte admin s'il n'existe pas
    db = SessionLocal()
    try:
        admin = db.query(User).filter_by(email="admin@sga.sn").first()
        if not admin:
            hashed = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            db.add(User(email="admin@sga.sn", nom="Admin", prenom="SGA",
                        password_hash=hashed, role="admin"))
            db.commit()
            print("Compte admin cree: admin@sga.sn / admin123")
        else:
            print("Compte admin existe deja.")
    finally:
        db.close()
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


# Page de login (HTML pur, pas de Dash)
@server.route("/login")
def login_page():
    return """<!DOCTYPE html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SGA - Connexion</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{font-family:'DM Sans',sans-serif;background:#f7f6f3;margin:0;display:flex;
align-items:center;justify-content:center;min-height:100vh;color:#37352f}
.login-card{background:#fff;padding:48px 40px;border-radius:8px;
border:1px solid #e8e8e4;max-width:380px;width:100%;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.brand-icon{width:44px;height:44px;background:#37352f;color:#fff;border-radius:8px;
display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:20px}
.form-control{border:1px solid #e8e8e4;border-radius:4px;padding:8px 12px;font-size:14px;
font-family:'DM Sans',sans-serif}
.form-control:focus{border-color:#37352f;box-shadow:none}
.btn-dark{background:#37352f;border:none;border-radius:4px;padding:8px 14px;font-size:14px;
font-weight:500;font-family:'DM Sans',sans-serif}
.btn-dark:hover{background:#2c2b28}
</style></head><body>
<div class="login-card">
<div style="text-align:center;margin-bottom:32px">
<div class="brand-icon">S</div>
<h2 style="font-weight:700;margin-top:12px">SGA</h2>
<p style="color:#73726e;font-size:14px">Systeme de Gestion Academique</p>
</div>
<form method="POST" action="/auth/login">
<input name="email" type="email" placeholder="Email" class="form-control mb-3" required>
<input name="password" type="password" placeholder="Mot de passe" class="form-control mb-3" required>
<button type="submit" class="btn btn-dark w-100 mb-3">Se connecter</button>
</form></div></body></html>"""


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
        # Flask before_request redirige vers /login, mais au cas ou :
        return html.Div([
            dcc.Location(id="url", refresh=True),
            dcc.Store(id="user-role", data=None),
            dcc.Store(id="user-teacher-id", data=None),
            html.P("Chargement..."),
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
