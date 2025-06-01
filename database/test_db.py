from database.queries import (
    add_teacher, add_classroom, add_group, add_subgroup, add_discipline,
    add_teacher_discipline, get_all_teachers, get_all_disciplines
)
from database.models import ClassroomType

def init_test_db():
    # Викладачі
    teachers = [
        ("Проф. Іванов", '{"Понеділок": ["8:30-10:00", "10:00-11:30"], "Вівторок": ["8:30-10:00"]}', 10),
        ("Доц. Петров", '{"Понеділок": ["10:00-11:30", "12:00-13:30"], "Середа": ["8:30-10:00"]}', 8),
        ("Проф. Сидоров", '{"Вівторок": ["10:00-11:30"], "Четвер": ["8:30-10:00"]}', 12),
        ("Доц. Коваленко", '{"Середа": ["10:00-11:30", "12:00-13:30"], "П\'ятниця": ["8:30-10:00"]}', 10),
        ("Проф. Шевченко", '{"Четвер": ["10:00-11:30"], "П\'ятниця": ["10:00-11:30"]}', 8),
        ("Доц. Бойко", '{"Понеділок": ["8:30-10:00"], "Вівторок": ["12:00-13:30"]}', 10),
        ("Проф. Грищенко", '{"Середа": ["8:30-10:00"], "Четвер": ["12:00-13:30"]}', 9),
        ("Доц. Ткаченко", '{"П\'ятниця": ["12:00-13:30"], "Вівторок": ["8:30-10:00"]}', 8),
        ("Проф. Лисенко", '{"Понеділок": ["12:00-13:30"], "Середа": ["10:00-11:30"]}', 10),
        ("Доц. Романенко", '{"Четвер": ["8:30-10:00"], "П\'ятниця": ["10:00-11:30"]}', 7),
    ]
    teacher_ids = []
    for name, availability, max_load in teachers:
        teacher_id = add_teacher(name, availability, max_load)
        teacher_ids.append(teacher_id)

    # Аудиторії
    classrooms = [
        ("101", 100, ClassroomType.LECTURE),  # Лекційна
        ("102", 100, ClassroomType.LECTURE),  # Лекційна
        ("104", 100, ClassroomType.LECTURE),  # Лекційна
        ("201", 30, ClassroomType.LAB),      # Лабораторна
        ("202", 30, ClassroomType.LAB),      # Лабораторна
        ("203", 30, ClassroomType.LAB),      # Лабораторна
        ("204", 30, ClassroomType.LAB),      # Лабораторна
    ]
    for number, capacity, type_ in classrooms:
        add_classroom(number, capacity, type_.value)

    # Групи та підгрупи
    groups = [
        ("КН-21", 60),
        ("КН-22", 55),
        ("ІП-21", 50),
        ("ІП-22", 45),
    ]
    group_ids = []
    for name, student_count in groups:
        group_id = add_group(name, student_count)
        group_ids.append(group_id)
        add_subgroup(group_id, f"{name}-1", student_count // 2)
        add_subgroup(group_id, f"{name}-2", student_count // 2)

    # Дисципліни
    disciplines = [
        "Математика",
        "Програмування",
        "Фізика",
        "Алгоритми",
        "Бази даних",
    ]
    discipline_ids = []
    for name in disciplines:
        discipline_id = add_discipline(name)
        discipline_ids.append(discipline_id)

    # Зв’язки викладачів і дисциплін
    teacher_discipline_pairs = [
        (0, 0),  # Іванов — Математика
        (1, 1),  # Петров — Програмування
        (2, 2),  # Сидоров — Фізика
        (3, 3),  # Коваленко — Алгоритми
        (4, 4),  # Шевченко — Бази даних
        (5, 1),  # Бойко — Програмування
        (6, 0),  # Грищенко — Математика
        (7, 3),  # Ткаченко — Алгоритми
        (8, 2),  # Лисенко — Фізика
        (9, 4),  # Романенко — Бази даних
    ]
    for teacher_idx, discipline_idx in teacher_discipline_pairs:
        add_teacher_discipline(teacher_ids[teacher_idx], discipline_ids[discipline_idx])

if __name__ == "__main__":
    init_test_db()
    print("Тестова база даних створена.")
    teachers = get_all_teachers()
    disciplines = get_all_disciplines()
    print(f"Викладачі: {[t.name for t in teachers]}")
    print(f"Дисципліни: {[d.name for d in disciplines]}")