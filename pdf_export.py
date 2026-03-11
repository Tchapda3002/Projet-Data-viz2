import io
from flask import send_file
from fpdf import FPDF
from sqlalchemy.orm import subqueryload, joinedload

from database import SessionLocal
from models import Student, Grade, Session, Attendance, Course


def generate_bulletin_pdf(student_id):
    """Genere un bulletin PDF pour un etudiant."""
    db = SessionLocal()
    try:
        student = db.query(Student).options(
            subqueryload(Student.grades).joinedload(Grade.course),
            subqueryload(Student.attendances),
        ).filter_by(id=student_id).first()

        if not student:
            return None

        total_sessions = db.query(Session).count()
        nb_presences = len(student.attendances)
        taux_presence = round((nb_presences / total_sessions) * 100, 1) if total_sessions > 0 else 0

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # En-tete
        pdf.set_font("Helvetica", "B", 20)
        pdf.cell(0, 12, "Bulletin de Notes", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(115, 114, 110)
        pdf.cell(0, 6, "Systeme de Gestion Academique (SGA)", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)

        # Ligne separatrice
        pdf.set_draw_color(232, 232, 228)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

        # Informations etudiant
        pdf.set_text_color(55, 53, 47)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Informations de l'etudiant", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Helvetica", "", 11)
        infos = [
            ("Nom complet", f"{student.prenom} {student.nom}"),
            ("Email", student.email),
            ("Date de naissance", str(student.date_naissance) if student.date_naissance else "-"),
            ("Taux de presence", f"{taux_presence}%"),
        ]
        for label, value in infos:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(50, 7, f"{label} :", new_x="RIGHT")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(8)

        # Tableau des notes
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Detail des notes", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # En-tete tableau
        col_widths = [70, 30, 25, 25, 40]
        headers = ["Cours", "Code", "Credits", "Note", "Appreciation"]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(247, 246, 243)

        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
        pdf.ln()

        # Lignes
        pdf.set_font("Helvetica", "", 9)
        total_points = 0
        total_credits = 0

        for g in student.grades:
            appreciation = "Excellent" if g.note >= 16 else "Bien" if g.note >= 14 else "Assez bien" if g.note >= 12 else "Passable" if g.note >= 10 else "Insuffisant"

            # Couleur selon la note
            if g.note >= 10:
                pdf.set_text_color(46, 204, 113)
            else:
                pdf.set_text_color(231, 76, 60)

            libelle = g.course.libelle[:35]
            pdf.cell(col_widths[0], 7, libelle, border=1)
            pdf.cell(col_widths[1], 7, g.course_code, border=1, align="C")
            pdf.cell(col_widths[2], 7, str(g.course.credits), border=1, align="C")
            pdf.cell(col_widths[3], 7, str(g.note), border=1, align="C")
            pdf.cell(col_widths[4], 7, appreciation, border=1, align="C")
            pdf.ln()

            total_points += g.note * g.course.credits
            total_credits += g.course.credits

        pdf.set_text_color(55, 53, 47)

        # Moyenne generale
        moyenne = round(total_points / total_credits, 2) if total_credits > 0 else 0
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        mention = "Tres bien" if moyenne >= 16 else "Bien" if moyenne >= 14 else "Assez bien" if moyenne >= 12 else "Passable" if moyenne >= 10 else "Ajourné"

        pdf.cell(0, 8, f"Moyenne generale : {moyenne}/20  -  Mention : {mention}",
                 new_x="LMARGIN", new_y="NEXT")

        # Credits totaux
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, f"Credits totaux : {total_credits}",
                 new_x="LMARGIN", new_y="NEXT")

        pdf.ln(12)
        pdf.set_draw_color(232, 232, 228)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        # Pied de page
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(155, 154, 151)
        pdf.cell(0, 6, "Document genere automatiquement par le SGA.", align="C")

        # Retourner le PDF en bytes
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        return output, f"bulletin_{student.nom}_{student.prenom}.pdf"

    finally:
        db.close()


def register_pdf_routes(server):
    """Enregistre les routes Flask pour l'export PDF."""

    @server.route("/api/bulletin/<int:student_id>")
    def download_bulletin(student_id):
        result = generate_bulletin_pdf(student_id)
        if not result:
            return "Etudiant introuvable", 404

        pdf_bytes, filename = result
        return send_file(pdf_bytes, download_name=filename, mimetype="application/pdf")
