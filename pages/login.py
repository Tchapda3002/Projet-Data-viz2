import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import bcrypt
from flask import session as flask_session

from database import SessionLocal
from models import User

dash.register_page(__name__, path="/login", name="Connexion")

layout = html.Div([
    html.Div([
        html.Div([
            html.Div("S", className="brand-icon-wrap"),
            html.H2("SGA", style={"fontWeight": "700", "marginTop": "12px"}),
            html.P("Systeme de Gestion Academique",
                   style={"color": "#73726e", "fontSize": "14px"}),
        ], style={"textAlign": "center", "marginBottom": "32px"}),

        dbc.Input(id="login-email", placeholder="Email", type="email", className="mb-3"),
        dbc.Input(id="login-password", placeholder="Mot de passe", type="password", className="mb-3"),
        dbc.Button("Se connecter", id="btn-login", color="dark", className="w-100 mb-3"),
        html.Div(id="login-alert"),
    ], className="login-card"),
], className="login-page")


@callback(
    Output("login-alert", "children"),
    Output("url", "pathname", allow_duplicate=True),
    Input("btn-login", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def do_login(n_clicks, email, password):
    if not email or not password:
        return dbc.Alert("Veuillez remplir tous les champs.", color="warning", duration=3000), no_update

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user:
            return dbc.Alert("Email ou mot de passe incorrect.", color="danger", duration=3000), no_update

        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            return dbc.Alert("Email ou mot de passe incorrect.", color="danger", duration=3000), no_update

        flask_session["user_id"] = user.id
        flask_session["user_email"] = user.email
        flask_session["user_role"] = user.role
        flask_session["user_nom"] = f"{user.prenom} {user.nom}"
        flask_session["teacher_id"] = user.teacher_id

        return no_update, "/"
    finally:
        db.close()
