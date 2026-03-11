from flask import jsonify, request
from database import SessionLocal
from models import Student, Teacher, Course, Session, Attendance, Grade


def register_api(server):
    """Enregistre les routes API REST sur le serveur Flask de Dash."""

    # --- Students ---

    @server.route("/api/students", methods=["GET"])
    def api_get_students():
        db = SessionLocal()
        try:
            students = db.query(Student).all()
            return jsonify([{
                "id": s.id, "nom": s.nom, "prenom": s.prenom,
                "email": s.email, "date_naissance": str(s.date_naissance),
            } for s in students])
        finally:
            db.close()

    @server.route("/api/students/<int:student_id>", methods=["GET"])
    def api_get_student(student_id):
        db = SessionLocal()
        try:
            s = db.query(Student).get(student_id)
            if not s:
                return jsonify({"error": "Etudiant non trouve"}), 404
            # Moyenne
            grades = db.query(Grade).filter(Grade.student_id == s.id).all()
            moyenne = round(sum(g.note for g in grades) / len(grades), 2) if grades else None
            # Taux presence
            all_sessions = db.query(Session).count()
            presences = db.query(Attendance).filter(Attendance.student_id == s.id).count()
            taux_presence = round((presences / all_sessions) * 100, 1) if all_sessions > 0 else 0
            return jsonify({
                "id": s.id, "nom": s.nom, "prenom": s.prenom,
                "email": s.email, "date_naissance": str(s.date_naissance),
                "moyenne": moyenne, "taux_presence": taux_presence,
                "notes": [{"course_code": g.course_code, "note": g.note} for g in grades],
            })
        finally:
            db.close()

    @server.route("/api/students", methods=["POST"])
    def api_create_student():
        db = SessionLocal()
        try:
            data = request.get_json()
            if not data or not data.get("nom") or not data.get("prenom"):
                return jsonify({"error": "nom et prenom requis"}), 400
            student = Student(
                nom=data["nom"], prenom=data["prenom"],
                email=data.get("email"), date_naissance=data.get("date_naissance"),
            )
            db.add(student)
            db.commit()
            return jsonify({"id": student.id, "message": "Etudiant cree"}), 201
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    @server.route("/api/students/<int:student_id>", methods=["DELETE"])
    def api_delete_student(student_id):
        db = SessionLocal()
        try:
            s = db.query(Student).get(student_id)
            if not s:
                return jsonify({"error": "Etudiant non trouve"}), 404
            db.query(Attendance).filter(Attendance.student_id == student_id).delete()
            db.query(Grade).filter(Grade.student_id == student_id).delete()
            db.delete(s)
            db.commit()
            return jsonify({"message": "Etudiant supprime"})
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    # --- Courses ---

    @server.route("/api/courses", methods=["GET"])
    def api_get_courses():
        db = SessionLocal()
        try:
            courses = db.query(Course).all()
            return jsonify([{
                "code": c.code, "libelle": c.libelle,
                "volume_horaire": c.volume_horaire, "credits": c.credits,
                "teacher_id": c.teacher_id,
                "enseignant": f"{c.teacher.prenom} {c.teacher.nom}" if c.teacher else None,
            } for c in courses])
        finally:
            db.close()

    @server.route("/api/courses/<string:code>", methods=["GET"])
    def api_get_course(code):
        db = SessionLocal()
        try:
            c = db.query(Course).get(code)
            if not c:
                return jsonify({"error": "Cours non trouve"}), 404
            sessions = db.query(Session).filter(Session.course_code == code).all()
            heures = sum(s.duree for s in sessions)
            grades = db.query(Grade).filter(Grade.course_code == code).all()
            moyenne = round(sum(g.note for g in grades) / len(grades), 2) if grades else None
            return jsonify({
                "code": c.code, "libelle": c.libelle,
                "volume_horaire": c.volume_horaire, "credits": c.credits,
                "enseignant": f"{c.teacher.prenom} {c.teacher.nom}" if c.teacher else None,
                "heures_effectuees": heures,
                "progression": round((heures / c.volume_horaire) * 100, 1) if c.volume_horaire > 0 else 0,
                "moyenne_classe": moyenne,
                "nb_sessions": len(sessions),
            })
        finally:
            db.close()

    @server.route("/api/courses", methods=["POST"])
    def api_create_course():
        db = SessionLocal()
        try:
            data = request.get_json()
            if not data or not data.get("code") or not data.get("libelle"):
                return jsonify({"error": "code et libelle requis"}), 400
            course = Course(
                code=data["code"], libelle=data["libelle"],
                volume_horaire=data.get("volume_horaire", 0),
                credits=data.get("credits", 1),
                teacher_id=data.get("teacher_id"),
            )
            db.add(course)
            db.commit()
            return jsonify({"code": course.code, "message": "Cours cree"}), 201
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    @server.route("/api/courses/<string:code>", methods=["DELETE"])
    def api_delete_course(code):
        db = SessionLocal()
        try:
            c = db.query(Course).get(code)
            if not c:
                return jsonify({"error": "Cours non trouve"}), 404
            # Cascade
            sessions = db.query(Session).filter(Session.course_code == code).all()
            session_ids = [s.id for s in sessions]
            if session_ids:
                db.query(Attendance).filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)
            db.query(Session).filter(Session.course_code == code).delete()
            db.query(Grade).filter(Grade.course_code == code).delete()
            db.delete(c)
            db.commit()
            return jsonify({"message": "Cours supprime"})
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    # --- Sessions ---

    @server.route("/api/sessions", methods=["GET"])
    def api_get_sessions():
        db = SessionLocal()
        try:
            course_filter = request.args.get("course")
            query = db.query(Session)
            if course_filter:
                query = query.filter(Session.course_code == course_filter)
            sessions = query.order_by(Session.date.desc()).all()
            return jsonify([{
                "id": s.id, "course_code": s.course_code,
                "date": str(s.date), "duree": s.duree, "theme": s.theme,
            } for s in sessions])
        finally:
            db.close()

    @server.route("/api/sessions", methods=["POST"])
    def api_create_session():
        db = SessionLocal()
        try:
            data = request.get_json()
            if not data or not data.get("course_code") or not data.get("date"):
                return jsonify({"error": "course_code et date requis"}), 400
            session = Session(
                course_code=data["course_code"], date=data["date"],
                duree=data.get("duree", 2), theme=data.get("theme", ""),
            )
            db.add(session)
            db.commit()
            return jsonify({"id": session.id, "message": "Seance creee"}), 201
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    # --- Grades ---

    @server.route("/api/grades", methods=["GET"])
    def api_get_grades():
        db = SessionLocal()
        try:
            course_filter = request.args.get("course")
            student_filter = request.args.get("student")
            query = db.query(Grade)
            if course_filter:
                query = query.filter(Grade.course_code == course_filter)
            if student_filter:
                query = query.filter(Grade.student_id == int(student_filter))
            grades = query.all()
            return jsonify([{
                "id": g.id, "student_id": g.student_id,
                "course_code": g.course_code, "note": g.note,
            } for g in grades])
        finally:
            db.close()

    @server.route("/api/grades", methods=["POST"])
    def api_create_grade():
        db = SessionLocal()
        try:
            data = request.get_json()
            if not data or not data.get("student_id") or not data.get("course_code"):
                return jsonify({"error": "student_id et course_code requis"}), 400
            grade = Grade(
                student_id=data["student_id"],
                course_code=data["course_code"],
                note=data.get("note", 0),
            )
            db.add(grade)
            db.commit()
            return jsonify({"id": grade.id, "message": "Note ajoutee"}), 201
        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()

    # --- Stats (KPIs) ---

    @server.route("/api/stats", methods=["GET"])
    def api_get_stats():
        db = SessionLocal()
        try:
            nb_students = db.query(Student).count()
            nb_courses = db.query(Course).count()
            nb_sessions = db.query(Session).count()
            nb_teachers = db.query(Teacher).count()
            nb_grades = db.query(Grade).count()
            nb_attendance = db.query(Attendance).count()

            # Moyenne generale
            grades = db.query(Grade).all()
            moyenne = round(sum(g.note for g in grades) / len(grades), 2) if grades else 0

            # Taux presence
            total_possible = nb_sessions * nb_students
            taux_presence = round((nb_attendance / total_possible) * 100, 1) if total_possible > 0 else 0

            # Taux reussite
            nb_reussite = sum(1 for g in grades if g.note >= 10)
            taux_reussite = round((nb_reussite / len(grades)) * 100, 1) if grades else 0

            return jsonify({
                "nb_students": nb_students,
                "nb_courses": nb_courses,
                "nb_sessions": nb_sessions,
                "nb_teachers": nb_teachers,
                "moyenne_generale": moyenne,
                "taux_presence": taux_presence,
                "taux_reussite": taux_reussite,
            })
        finally:
            db.close()
