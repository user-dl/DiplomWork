import random
import json
import logging
from database.queries import (
    get_all_groups, get_all_subgroups, get_all_teachers, get_all_classrooms,
    get_all_disciplines, get_teachers_for_discipline, get_classrooms_by_type,
    get_teacher_by_id, get_group_by_id, get_subgroup_by_id, get_classroom_by_id,
    add_schedule, Session
)
from database.models import (
    LessonType, ClassroomType, Teacher, Classroom, Group, Subgroup, Discipline
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_data():
    """Завантажує дані з бази для генерації розкладу."""
    logger.info("Завантаження даних із бази...")
    session = Session()
    try:
        groups = session.query(Group).all()
        subgroups = session.query(Subgroup).all()
        teachers = session.query(Teacher).all()
        classrooms = session.query(Classroom).all()
        disciplines = session.query(Discipline).all()

        logger.info(
            f"Знайдено: груп={len(groups)}, підгруп={len(subgroups)}, викладачів={len(teachers)}, "
            f"аудиторій={len(classrooms)}, дисциплін={len(disciplines)}"
        )

        if not all([groups, subgroups, teachers, classrooms, disciplines]):
            raise ValueError("Дані в базі неповні. Запустіть test_db.py.")

        return {
            "groups": groups,
            "subgroups": subgroups,
            "teacher_ids": [t.id for t in teachers],
            "classroom_ids": [c.id for c in classrooms],
            "discipline_ids": [d.id for d in disciplines],
            "time_slots": [
                "Понеділок 8:30-10:00", "Понеділок 10:00-11:30", "Понеділок 12:00-13:30", "Понеділок 13:30-15:00",
                "Вівторок 8:30-10:00", "Вівторок 10:00-11:30", "Вівторок 12:00-13:30", "Вівторок 13:30-15:00",
                "Середа 8:30-10:00", "Середа 10:00-11:30", "Середа 12:00-13:30", "Середа 13:30-15:00",
                "Четвер 8:30-10:00", "Четвер 10:00-11:30", "Четвер 12:00-13:30", "Четвер 13:30-15:00",
                "П'ятниця 8:30-10:00", "П'ятниця 10:00-11:30", "П'ятниця 12:00-13:30", "П'ятниця 13:30-15:00"
            ],
        }
    finally:
        session.close()

def generate_slot(data, group=None, subgroup=None, discipline_id=None, lesson_type=None):
    """Генерує одне заняття з випадковими параметрами."""
    if lesson_type == LessonType.LECTURE.value:
        group_id = group.id if group else None
        subgroup_id = None
        student_count = group.student_count if group else 0
    else:
        group_id = None
        subgroup_id = subgroup.id if subgroup else None
        student_count = subgroup.student_count if subgroup else 0

    # Вибираємо викладача
    teacher_ids = get_teachers_for_discipline(discipline_id)
    teacher_id = random.choice(teacher_ids) if teacher_ids else random.choice(data["teacher_ids"])

    # Вибираємо аудиторію
    suitable_classrooms = get_classrooms_by_type(
        ClassroomType.LECTURE if lesson_type == LessonType.LECTURE.value else ClassroomType.LAB
    )
    suitable_classrooms = [c for c in suitable_classrooms if c.capacity >= student_count]
    classroom_id = random.choice([c.id for c in suitable_classrooms]) if suitable_classrooms else random.choice(data["classroom_ids"])

    # Вибираємо випадковий часовий слот
    time_slot = random.choice(data["time_slots"])

    return {
        "group_id": group_id,
        "subgroup_id": subgroup_id,
        "teacher_id": teacher_id,
        "classroom_id": classroom_id,
        "discipline_id": discipline_id,
        "lesson_type": lesson_type,
        "time_slot": time_slot,
        "group_student_count": student_count if group_id else 0,
        "subgroup_student_count": student_count if subgroup_id else 0,
    }

def run_random_search():
    """Запускає випадковий пошук для створення розкладу."""
    logger.info("Запуск випадкового пошуку...")
    data = load_data()
    schedule = []

    # Лекції для груп
    for group in data["groups"]:
        for discipline_id in data["discipline_ids"]:
            slot = generate_slot(
                data, group=group, discipline_id=discipline_id,
                lesson_type=LessonType.LECTURE.value
            )
            schedule.append(slot)

    # Лабораторні для підгруп
    for group in data["groups"]:
        subgroups = [s for s in data["subgroups"] if s.group_id == group.id]
        if len(subgroups) < 2:
            logger.warning(f"Група {group.name} має менше 2 підгруп!")
            continue
        for subgroup in subgroups:
            for discipline_id in data["discipline_ids"]:
                slot = generate_slot(
                    data, subgroup=subgroup, discipline_id=discipline_id,
                    lesson_type=LessonType.LAB.value
                )
                schedule.append(slot)

    # Збереження розкладу в базу
    session = Session()
    try:
        for slot in schedule:
            add_schedule(
                group_id=slot.get("group_id"),
                subgroup_id=slot.get("subgroup_id"),
                teacher_id=slot["teacher_id"],
                classroom_id=slot["classroom_id"],
                discipline_id=slot["discipline_id"],
                lesson_type=slot["lesson_type"],
                time_slot=slot["time_slot"]
            )
        session.commit()
        logger.info("Розклад збережено в базу даних")
    except Exception as e:
        session.rollback()
        logger.error(f"Помилка збереження розкладу: {e}")
    finally:
        session.close()

    # Логування результатів
    kn21_count = sum(1 for slot in schedule if slot.get("group_id") and
                     get_group_by_id(slot["group_id"]).name == "КН-21")
    logger.info(f"Генерація завершена. Занять: {len(schedule)}")
    logger.info(f"Занять для КН-21: {kn21_count}")

    # Дебаг-вивід розкладу
    logger.info("Фінальний розклад:")
    for slot in schedule:
        group = get_group_by_id(slot["group_id"]).name if slot["group_id"] else "-"
        subgroup = get_subgroup_by_id(slot["subgroup_id"]).name if slot["subgroup_id"] else "-"
        logger.info(f"Група: {group}, Підгрупа: {subgroup}, Час: {slot['time_slot']}, Тип: {slot['lesson_type']}")

    return schedule

if __name__ == "__main__":
    try:
        schedule = run_random_search()
        logger.info("Розклад згенеровано")
    except Exception as e:
        logger.error(f"Помилка: {e}")