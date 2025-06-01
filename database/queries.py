from sqlalchemy.orm import sessionmaker
from database.models import Teacher, Classroom, Group, Subgroup, Discipline, Schedule, Base, teacher_disciplines, LessonType, ClassroomType
from sqlalchemy import create_engine
from sqlalchemy.sql import insert, delete
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)

engine = create_engine("sqlite:///C:/Users/user/PycharmProjects/DiplomWork/schedule.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def add_teacher(name, availability, max_load=10):
    session = Session()
    try:
        teacher = Teacher(name=name, availability=availability, max_load=max_load)
        session.add(teacher)
        session.commit()
        return teacher.id
    finally:
        session.close()

def add_teacher_discipline(teacher_id, discipline_id):
    session = Session()
    try:
        stmt = insert(teacher_disciplines).values(teacher_id=teacher_id, discipline_id=discipline_id)
        session.execute(stmt)
        session.commit()
    finally:
        session.close()

def add_classroom(number, capacity, type=ClassroomType.LECTURE):
    session = Session()
    try:
        classroom = Classroom(number=number, capacity=capacity, type=type)
        session.add(classroom)
        session.commit()
        return classroom.id
    finally:
        session.close()

def add_group(name, student_count):
    session = Session()
    try:
        group = Group(name=name, student_count=student_count)
        session.add(group)
        session.commit()
        return group.id
    finally:
        session.close()

def add_subgroup(group_id, name, student_count):
    session = Session()
    try:
        subgroup = Subgroup(group_id=group_id, name=name, student_count=student_count)
        session.add(subgroup)
        session.commit()
        return subgroup.id
    finally:
        session.close()

def add_discipline(name):
    session = Session()
    try:
        discipline = Discipline(name=name)
        session.add(discipline)
        session.commit()
        return discipline.id
    finally:
        session.close()

def add_schedule(group_id=None, subgroup_id=None, teacher_id=None, classroom_id=None, discipline_id=None, lesson_type=None, time_slot=None):
    session = Session()
    try:
        schedule = Schedule(
            group_id=group_id,
            subgroup_id=subgroup_id,
            teacher_id=teacher_id,
            classroom_id=classroom_id,
            discipline_id=discipline_id,
            lesson_type=lesson_type,
            time_slot=time_slot
        )
        session.add(schedule)
        session.commit()
        return schedule.id
    finally:
        session.close()

def update_schedule(schedule_id, group_id=None, subgroup_id=None, teacher_id=None, classroom_id=None, discipline_id=None, lesson_type=None, time_slot=None):
    session = Session()
    try:
        schedule = session.query(Schedule).filter_by(id=schedule_id).first()
        if schedule:
            if group_id is not None:
                schedule.group_id = group_id
            if subgroup_id is not None:
                schedule.subgroup_id = subgroup_id
            if teacher_id is not None:
                schedule.teacher_id = teacher_id
            if classroom_id is not None:
                schedule.classroom_id = classroom_id
            if discipline_id is not None:
                schedule.discipline_id = discipline_id
            if lesson_type is not None:
                schedule.lesson_type = lesson_type
            if time_slot is not None:
                schedule.time_slot = time_slot
            session.commit()
    finally:
        session.close()

def get_schedule_by_group(group_id):
    session = Session()
    try:
        return session.query(Schedule).filter_by(group_id=group_id).all()
    finally:
        session.close()

def get_schedule_by_subgroup(subgroup_id):
    session = Session()
    try:
        return session.query(Schedule).filter_by(subgroup_id=subgroup_id).all()
    finally:
        session.close()

def get_teacher_by_id(teacher_id):
    session = Session()
    try:
        return session.query(Teacher).filter_by(id=teacher_id).first()
    finally:
        session.close()

def get_classroom_by_id(classroom_id):
    session = Session()
    try:
        return session.query(Classroom).filter_by(id=classroom_id).first()
    finally:
        session.close()

def get_group_by_id(group_id):
    session = Session()
    try:
        return session.query(Group).filter_by(id=group_id).first()
    finally:
        session.close()

def get_subgroup_by_id(subgroup_id):
    session = Session()
    try:
        return session.query(Subgroup).filter_by(id=subgroup_id).first()
    finally:
        session.close()

def get_discipline_by_id(discipline_id):
    session = Session()
    try:
        return session.query(Discipline).filter_by(id=discipline_id).first()
    finally:
        session.close()

def get_teachers_for_discipline(discipline_id):
    session = Session()
    try:
        discipline = session.query(Discipline).filter_by(id=discipline_id).first()
        if discipline:
            return [teacher.id for teacher in discipline.teachers]
        return []
    finally:
        session.close()

def get_all_teachers():
    session = Session()
    try:
        return session.query(Teacher).all()
    finally:
        session.close()

def get_all_classrooms():
    session = Session()
    try:
        return session.query(Classroom).all()
    finally:
        session.close()

def get_all_groups():
    session = Session()
    try:
        return session.query(Group).all()
    finally:
        session.close()

def get_all_subgroups():
    session = Session()
    try:
        return session.query(Subgroup).all()
    finally:
        session.close()

def get_all_disciplines():
    session = Session()
    try:
        return session.query(Discipline).all()
    finally:
        session.close()

# Функція для отримання аудиторій за типом (додано для simulated_annealing.py)
def get_classrooms_by_type(classroom_type):
    session = Session()
    try:
        classrooms = session.query(Classroom).filter_by(type=classroom_type).all()
        if not classrooms:
            logger.warning(f"Немає аудиторій типу {classroom_type}")
        return classrooms
    finally:
        session.close()

def delete_teacher(teacher_id):
    session = Session()
    try:
        # Перевірка, чи викладач використовується в розкладі
        if session.query(Schedule).filter_by(teacher_id=teacher_id).count() > 0:
            raise ValueError("Викладач використовується в розкладі")
        # Видалити зв’язки з дисциплінами
        session.execute(delete(teacher_disciplines).where(teacher_disciplines.c.teacher_id == teacher_id))
        # Видалити викладача
        teacher = session.query(Teacher).filter_by(id=teacher_id).first()
        if teacher:
            session.delete(teacher)
            session.commit()
        else:
            raise ValueError("Викладач не знайдений")
    except IntegrityError:
        session.rollback()
        raise ValueError("Помилка видалення: викладач має зв’язки")
    finally:
        session.close()

def delete_classroom(classroom_id):
    session = Session()
    try:
        # Перевірка, чи аудиторія використовується в розкладі
        if session.query(Schedule).filter_by(classroom_id=classroom_id).count() > 0:
            raise ValueError("Аудиторія використовується в розкладі")
        classroom = session.query(Classroom).filter_by(id=classroom_id).first()
        if classroom:
            session.delete(classroom)
            session.commit()
        else:
            raise ValueError("Аудиторія не знайдена")
    except IntegrityError:
        session.rollback()
        raise ValueError("Помилка видалення аудиторії")
    finally:
        session.close()

def delete_group(group_id):
    session = Session()
    try:
        # Перевірка, чи група використовується в розкладі
        if session.query(Schedule).filter_by(group_id=group_id).count() > 0:
            raise ValueError("Група використовується в розкладі")
        # Перевірка, чи є підгрупи в розкладі
        if session.query(Schedule).join(Subgroup).filter(Subgroup.group_id == group_id).count() > 0:
            raise ValueError("Підгрупи групи використовуються в розкладі")
        # Видалити підгрупи
        session.query(Subgroup).filter_by(group_id=group_id).delete()
        # Видалити групу
        group = session.query(Group).filter_by(id=group_id).first()
        if group:
            session.delete(group)
            session.commit()
        else:
            raise ValueError("Група не знайдена")
    except IntegrityError:
        session.rollback()
        raise ValueError("Помилка видалення групи")
    finally:
        session.close()

def delete_subgroup(subgroup_id):
    session = Session()
    try:
        # Перевірка, чи підгрупа використовується в розкладі
        if session.query(Schedule).filter_by(subgroup_id=subgroup_id).count() > 0:
            raise ValueError("Підгрупа використовується в розкладі")
        subgroup = session.query(Subgroup).filter_by(id=subgroup_id).first()
        if subgroup:
            session.delete(subgroup)
            session.commit()
        else:
            raise ValueError("Підгрупа не знайдена")
    except IntegrityError:
        session.rollback()
        raise ValueError("Помилка видалення підгрупи")
    finally:
        session.close()

def delete_discipline(discipline_id):
    session = Session()
    try:
        # Перевірка, чи дисципліна використовується в розкладі
        if session.query(Schedule).filter_by(discipline_id=discipline_id).count() > 0:
            raise ValueError("Дисципліна використовується в розкладі")
        # Видалити зв’язки з викладачами
        session.execute(delete(teacher_disciplines).where(teacher_disciplines.c.discipline_id == discipline_id))
        # Видалити дисципліну
        discipline = session.query(Discipline).filter_by(id=discipline_id).first()
        if discipline:
            session.delete(discipline)
            session.commit()
        else:
            raise ValueError("Дисципліна не знайдена")
    except IntegrityError:
        session.rollback()
        raise ValueError("Помилка видалення дисципліни")
    finally:
        session.close()

def delete_schedule(schedule_id=None):
    session = Session()
    try:
        if schedule_id:
            schedule = session.query(Schedule).filter_by(id=schedule_id).first()
            if schedule:
                session.delete(schedule)
                session.commit()
            else:
                raise ValueError("Запис розкладу не знайдено")
        else:
            # Видалити весь розклад
            session.query(Schedule).delete()
            session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("Помилка видалення розкладу")
    finally:
        session.close()