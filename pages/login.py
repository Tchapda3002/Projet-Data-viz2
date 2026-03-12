import dash
from dash import html

dash.register_page(__name__, path="/login", name="Connexion")

layout = html.Div(id="login-placeholder")
