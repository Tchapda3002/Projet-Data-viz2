import dash
from dash import html, dcc, callback, Input, Output, State, dash_table, no_update
import dash_bootstrap_components as dbc
import bcrypt

from database import SessionLocal
from models import Teacher, User, Course

dash.register_page(__name__, path="/admin", name="Administration")


def get_teachers():
    db = SessionLocal()
    try:
        teachers = db.query(Teacher).order_by(Teacher.nom).all()
        return [
            {"ID": t.id, "Nom": t.nom, "Prenom": t.prenom,
             "Email": t.email or "", "Telephone": t.telephone or ""}
            for t in teachers
        ]
    finally:
        db.close()


def get_users():
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.nom).all()
        return [
            {"ID": u.id, "Email": u.email, "Nom": u.nom, "Prenom": u.prenom,
             "Role": u.role, "Teacher ID": u.teacher_id or ""}
            for u in users
        ]
    finally:
        db.close()


def get_teachers_dropdown():
    db = SessionLocal()
    try:
        teachers = db.query(Teacher).order_by(Teacher.nom).all()
        return [{"label": f"{t.prenom} {t.nom}", "value": t.id} for t in teachers]
    finally:
        db.close()


# --- Layout ---

def layout():
    return html.Div([
        html.H1("Administration"),

        # --- Gestion Enseignants ---
        html.H3("Gestion des enseignants"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Nom"),
                dbc.Input(id="input-teacher-nom", placeholder="Nom"),
            ], width=3),
            dbc.Col([
                dbc.Label("Prenom"),
                dbc.Input(id="input-teacher-prenom", placeholder="Prenom"),
            ], width=3),
            dbc.Col([
                dbc.Label("Email"),
                dbc.Input(id="input-teacher-email", placeholder="email@example.com", type="email"),
            ], width=3),
            dbc.Col([
                dbc.Label("Telephone"),
                dbc.Input(id="input-teacher-tel", placeholder="+221..."),
            ], width=3),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Ajouter l'enseignant", id="btn-add-teacher", color="dark", className="me-2"),
                dbc.Button("Supprimer la selection", id="btn-del-teacher", color="danger", outline=True),
            ]),
        ]),
        html.Div(id="teacher-alert", className="mt-2"),
        html.Div(id="teachers-table", className="mt-3"),

        html.Hr(),

        # --- Gestion Comptes Utilisateurs ---
        html.H3("Gestion des comptes utilisateurs"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Email"),
                dbc.Input(id="input-user-email", placeholder="email@example.com", type="email"),
            ], width=3),
            dbc.Col([
                dbc.Label("Nom"),
                dbc.Input(id="input-user-nom", placeholder="Nom"),
            ], width=2),
            dbc.Col([
                dbc.Label("Prenom"),
                dbc.Input(id="input-user-prenom", placeholder="Prenom"),
            ], width=2),
            dbc.Col([
                dbc.Label("Mot de passe"),
                dbc.Input(id="input-user-password", type="password", placeholder="********"),
            ], width=2),
            dbc.Col([
                dbc.Label("Role"),
                dcc.Dropdown(id="input-user-role", options=[
                    {"label": "Administrateur", "value": "admin"},
                    {"label": "Enseignant", "value": "enseignant"},
                ], value="enseignant"),
            ], width=1),
            dbc.Col([
                dbc.Label("Enseignant lie"),
                dcc.Dropdown(id="input-user-teacher", placeholder="Aucun"),
            ], width=2),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button("Creer le compte", id="btn-add-user", color="dark", className="me-2"),
                dbc.Button("Supprimer la selection", id="btn-del-user", color="danger", outline=True),
            ]),
        ]),
        html.Div(id="user-alert", className="mt-2"),
        html.Div(id="users-table", className="mt-3"),
    ])


# --- Callbacks Enseignants ---

@callback(
    Output("teacher-alert", "children"),
    Input("btn-add-teacher", "n_clicks"),
    Input("btn-del-teacher", "n_clicks"),
    State("input-teacher-nom", "value"),
    State("input-teacher-prenom", "value"),
    State("input-teacher-email", "value"),
    State("input-teacher-tel", "value"),
    State("teacher-datatable", "selected_rows"),
    State("teacher-datatable", "data"),
    prevent_initial_call=True,
)
def manage_teacher(add_clicks, del_clicks, nom, prenom, email, tel, selected_rows, table_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    db = SessionLocal()

    try:
        if trigger == "btn-add-teacher":
            if not all([nom, prenom]):
                return dbc.Alert("Nom et prenom sont requis.", color="warning", duration=3000)
            if email:
                existing = db.query(Teacher).filter_by(email=email).first()
                if existing:
                    return dbc.Alert(f"L'email '{email}' existe deja.", color="danger", duration=3000)
            teacher = Teacher(nom=nom, prenom=prenom, email=email, telephone=tel)
            db.add(teacher)
            db.commit()
            return dbc.Alert(f"Enseignant '{prenom} {nom}' ajoute.", color="success", duration=3000)

        elif trigger == "btn-del-teacher":
            if not selected_rows:
                return dbc.Alert("Selectionnez un enseignant.", color="warning", duration=3000)
            teacher_id = table_data[selected_rows[0]]["ID"]
            # Verifier qu'aucun cours n'est lie
            courses = db.query(Course).filter_by(teacher_id=teacher_id).count()
            if courses > 0:
                return dbc.Alert(
                    f"Impossible : {courses} cours sont lies a cet enseignant. Supprimez-les d'abord.",
                    color="danger", duration=5000,
                )
            # Supprimer le compte utilisateur lie
            db.query(User).filter_by(teacher_id=teacher_id).delete()
            teacher = db.query(Teacher).filter_by(id=teacher_id).first()
            if teacher:
                db.delete(teacher)
                db.commit()
                return dbc.Alert("Enseignant supprime.", color="info", duration=3000)
    except Exception as e:
        db.rollback()
        return dbc.Alert(f"Erreur : {e}", color="danger", duration=5000)
    finally:
        db.close()

    return no_update


@callback(
    Output("teachers-table", "children"),
    Input("teacher-alert", "children"),
)
def refresh_teachers(_):
    data = get_teachers()
    if not data:
        return html.P("Aucun enseignant.")

    return dash_table.DataTable(
        id="teacher-datatable",
        data=data,
        columns=[{"name": k, "id": k} for k in data[0].keys()],
        row_selectable="single",
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#f7f6f3", "fontWeight": "600",
                      "border": "1px solid #e8e8e4"},
        style_cell={"textAlign": "left", "padding": "8px 12px",
                    "border": "1px solid #e8e8e4", "fontSize": "14px"},
        page_size=15,
    )


# --- Callbacks Utilisateurs ---

@callback(
    Output("input-user-teacher", "options"),
    Input("teachers-table", "children"),
)
def load_teacher_dropdown(_):
    return get_teachers_dropdown()


@callback(
    Output("user-alert", "children"),
    Input("btn-add-user", "n_clicks"),
    Input("btn-del-user", "n_clicks"),
    State("input-user-email", "value"),
    State("input-user-nom", "value"),
    State("input-user-prenom", "value"),
    State("input-user-password", "value"),
    State("input-user-role", "value"),
    State("input-user-teacher", "value"),
    State("user-datatable", "selected_rows"),
    State("user-datatable", "data"),
    prevent_initial_call=True,
)
def manage_user(add_clicks, del_clicks, email, nom, prenom, password, role, teacher_id,
                selected_rows, table_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    db = SessionLocal()

    try:
        if trigger == "btn-add-user":
            if not all([email, nom, prenom, password, role]):
                return dbc.Alert("Tous les champs sont requis.", color="warning", duration=3000)
            existing = db.query(User).filter_by(email=email).first()
            if existing:
                return dbc.Alert(f"L'email '{email}' existe deja.", color="danger", duration=3000)
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            user = User(
                email=email, nom=nom, prenom=prenom,
                password_hash=hashed, role=role,
                teacher_id=int(teacher_id) if teacher_id else None,
            )
            db.add(user)
            db.commit()
            return dbc.Alert(f"Compte '{email}' cree ({role}).", color="success", duration=3000)

        elif trigger == "btn-del-user":
            if not selected_rows:
                return dbc.Alert("Selectionnez un compte.", color="warning", duration=3000)
            user_id = table_data[selected_rows[0]]["ID"]
            user = db.query(User).filter_by(id=user_id).first()
            if user:
                db.delete(user)
                db.commit()
                return dbc.Alert(f"Compte '{user.email}' supprime.", color="info", duration=3000)
    except Exception as e:
        db.rollback()
        return dbc.Alert(f"Erreur : {e}", color="danger", duration=5000)
    finally:
        db.close()

    return no_update


@callback(
    Output("users-table", "children"),
    Input("user-alert", "children"),
)
def refresh_users(_):
    data = get_users()
    if not data:
        return html.P("Aucun utilisateur.")

    return dash_table.DataTable(
        id="user-datatable",
        data=data,
        columns=[{"name": k, "id": k} for k in data[0].keys() if k != "ID"],
        row_selectable="single",
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#f7f6f3", "fontWeight": "600",
                      "border": "1px solid #e8e8e4"},
        style_cell={"textAlign": "left", "padding": "8px 12px",
                    "border": "1px solid #e8e8e4", "fontSize": "14px"},
        page_size=15,
    )
