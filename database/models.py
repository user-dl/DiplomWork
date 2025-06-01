from enum import Enum
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import Enum as SQLEnum
from sqlalchemy.orm import relationship

Base = declarative_base()

class LessonType(str, Enum):
    LECTURE = "LECTURE"
    LAB = "LAB"

class ClassroomType(str, Enum):
    LECTURE = "LECTURE"
    LAB = "LAB"

teacher_disciplines = Table(
    "teacher_disciplines",
    Base.metadata,
    Column("teacher_id", Integer, ForeignKey("teachers.id"), primary_key=True),
    Column("discipline_id", Integer, ForeignKey("disciplines.id"), primary_key=True)
)

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    availability = Column(String)  # JSON string
    max_load = Column(Integer, nullable=False, default=10)  # Максимум занять/тиждень
    disciplines = relationship("Discipline", secondary=teacher_disciplines, back_populates="teachers")

class Classroom(Base):
    __tablename__ = "classrooms"
    id = Column(Integer, primary_key=True)
    number = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    type = Column(SQLEnum(ClassroomType), nullable=False, default=ClassroomType.LECTURE)

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    student_count = Column(Integer, nullable=False)

class Subgroup(Base):
    __tablename__ = "subgroups"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    name = Column(String, nullable=False)
    student_count = Column(Integer, nullable=False)

class Discipline(Base):
    __tablename__ = "disciplines"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    teachers = relationship("Teacher", secondary=teacher_disciplines, back_populates="disciplines")

class Schedule(Base):
    __tablename__ = "schedule"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    subgroup_id = Column(Integer, ForeignKey("subgroups.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    discipline_id = Column(Integer, ForeignKey("disciplines.id"), nullable=False)
    lesson_type = Column(SQLEnum(LessonType), nullable=False)
    time_slot = Column(String, nullable=False)