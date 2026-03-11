# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Description du Projet

Application web de gestion academique (cours, seances, presences, notes) avec tableaux de bord et visualisations. Specifications detaillees dans `Projet dataviz2.pdf`.

## Stack Technique

- **Langage** : Python
- **Framework Web** : Dash (Plotly)
- **ORM** : SQLAlchemy
- **Base de donnees** : SQLite (dev) / PostgreSQL (prod possible)
- **Visualisation** : Plotly
- **Fichiers Excel** : pandas / openpyxl

## Commandes

```bash
pip install -r requirements.txt   # Installation des dependances
python app.py                     # Lancement de l'application Dash
```

## Architecture Cible

Organisation modulaire : un fichier par page Dash, un fichier pour les modeles SQLAlchemy.

```
app.py                  # Point d'entree Dash
models.py               # Modeles SQLAlchemy (Students, Courses, Sessions, Attendance, Grades)
pages/
  module0.py            # Initialisation SQL + Migration Excel
  module1.py            # CRUD Cours + Suivi progression (barre de progression)
  module2.py            # Enregistrement seances + Appel numerique + Historique
  module3.py            # Tableau de bord etudiant + Workflow Note-Excel
```

## Schema de Base de Donnees

5 tables relationnelles :
- **Students** : id (PK), nom, prenom, email, date_naissance
- **Courses** : code (PK), libelle, volume_horaire_total, enseignant
- **Sessions** : id (PK), course_code (FK -> Courses), date, duree, theme
- **Attendance** : session_id (FK -> Sessions), student_id (FK -> Students) — table de liaison
- **Grades** : student_id (FK -> Students), course_code (FK -> Courses), note, coefficient

## Modules Fonctionnels

| Module | Fonctionnalites |
|--------|----------------|
| Module 0 | Initialisation tables SQL + Import Excel vers DB |
| Module 1 | CRUD Cours + Barre de progression (heures effectuees / volume total) |
| Module 2 | Creation seances + Appel numerique (checkboxes) + Historique des seances |
| Module 3 | Dashboard etudiant (notes, absences) + Export/Import notes via Excel |
| Bonus | Authentification (Dash Auth), graphiques avances, export PDF |

## Etat du Projet

- [ ] Structure initiale et dependances
- [ ] Module 0 : Init DB + Migration Excel
- [ ] Module 1 : Gestion des cours
- [ ] Module 2 : Seances et presences
- [ ] Module 3 : Notes et dashboard etudiant
- [ ] Bonus

## Decisions Techniques

_(A completer au fur et a mesure)_

## Problemes Resolus

_(A completer au fur et a mesure)_
