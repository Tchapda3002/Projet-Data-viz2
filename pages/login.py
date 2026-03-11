import dash
from dash import html, dcc

dash.register_page(__name__, path="/login", name="Connexion")

# Le login est gere par une route Flask POST dans app.py
# On affiche juste un formulaire HTML classique qui poste vers /auth/login

layout = html.Div([
    html.Div([
        html.Div([
            html.Div("S", className="brand-icon-wrap"),
            html.H2("SGA", style={"fontWeight": "700", "marginTop": "12px"}),
            html.P("Systeme de Gestion Academique",
                   style={"color": "#73726e", "fontSize": "14px"}),
        ], style={"textAlign": "center", "marginBottom": "32px"}),

        html.Form([
            html.Div([
                html.Input(
                    name="email", type="email", placeholder="Email",
                    className="form-control mb-3",
                    required=True,
                ),
            ]),
            html.Div([
                html.Input(
                    name="password", type="password", placeholder="Mot de passe",
                    className="form-control mb-3",
                    required=True,
                ),
            ]),
            html.Button(
                "Se connecter", type="submit",
                className="btn btn-dark w-100 mb-3",
            ),
        ], method="POST", action="/auth/login"),

        html.Div(id="login-alert"),
    ], className="login-card"),
], className="login-page")
