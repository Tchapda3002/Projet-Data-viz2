from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "admin" ou "enseignant"
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    email = Column(String, unique=True)
    telephone = Column(String)

    courses = relationship("Course", back_populates="teacher")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    date_naissance = Column(Date)

    attendances = relationship("Attendance", back_populates="student")
    grades = relationship("Grade", back_populates="student")


class Course(Base):
    __tablename__ = "courses"

    code = Column(String, primary_key=True)
    libelle = Column(String, nullable=False)
    volume_horaire = Column(Float, nullable=False)
    credits = Column(Float, nullable=False, default=1.0)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)

    teacher = relationship("Teacher", back_populates="courses")
    sessions = relationship("Session", back_populates="course")
    grades = relationship("Grade", back_populates="course")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    course_code = Column(String, ForeignKey("courses.code"), nullable=False)
    date = Column(Date, nullable=False)
    duree = Column(Float, nullable=False)
    theme = Column(String)

    course = relationship("Course", back_populates="sessions")
    attendances = relationship("Attendance", back_populates="session")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance"),
    )

    session = relationship("Session", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_code = Column(String, ForeignKey("courses.code"), nullable=False)
    note = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "course_code", name="uq_grade"),
    )

    student = relationship("Student", back_populates="grades")
    course = relationship("Course", back_populates="grades")
