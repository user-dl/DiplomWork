import random
import math
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
    """Генерує одне заняття для групи або підгрупи."""
    if lesson_type == LessonType.LECTURE.value:
        group_id = group.id if group else None
        subgroup_id = None
        student_count = group.student_count if group else 0
    else:
        group_id = None
        subgroup_id = subgroup.id if subgroup else None
        student_count = subgroup.student_count if subgroup else 0

    teacher_ids = get_teachers_for_discipline(discipline_id)
    teacher_id = random.choice(teacher_ids) if teacher_ids else random.choice(data["teacher_ids"])

    # Вибираємо аудиторію за типом і місткістю
    suitable_classrooms = get_classrooms_by_type(
        ClassroomType.LECTURE if lesson_type == LessonType.LECTURE.value else ClassroomType.LAB
    )
    suitable_classrooms = [c for c in suitable_classrooms if c.capacity >= student_count]
    classroom_id = random.choice([c.id for c in suitable_classrooms]) if suitable_classrooms else random.choice(data["classroom_ids"])

    # Вибираємо часовий слот, надаючи перевагу ранковим для лекцій і післяобіднім для лабораторних
    time_slots = data["time_slots"]
    if lesson_type == LessonType.LECTURE.value:
        morning_slots = [ts for ts in time_slots if "8:30" in ts or "10:00" in ts]
        time_slot = random.choice(morning_slots) if morning_slots else random.choice(time_slots)
    else:
        afternoon_slots = [ts for ts in time_slots if "12:00" in ts or "13:30" in ts]
        time_slot = random.choice(afternoon_slots) if afternoon_slots else random.choice(time_slots)

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

def generate_initial_schedule():
    """Генерує початковий розклад для всіх груп і підгруп."""
    logger.info("Генерація початкового розкладу...")
    data = load_data()
    schedule = []

    # Лекції для груп
    for group in data["groups"]:
        for discipline_id in data["discipline_ids"]:
            lecture_slot = generate_slot(
                data, group=group, discipline_id=discipline_id, lesson_type=LessonType.LECTURE.value
            )
            schedule.append(lecture_slot)

    # Лабораторні для підгруп
    for group in data["groups"]:
        subgroups = [s for s in data["subgroups"] if s.group_id == group.id]
        if len(subgroups) < 2:
            logger.warning(f"Група {group.name} має менше 2 підгруп!")
            continue
        for subgroup in subgroups:
            for discipline_id in data["discipline_ids"]:
                lab_slot = generate_slot(
                    data, subgroup=subgroup, discipline_id=discipline_id,
                    lesson_type=LessonType.LAB.value
                )
                schedule.append(lab_slot)

    logger.info(f"Згенеровано початковий розклад: {len(schedule)} занять")
    return schedule

def evaluate_schedule(schedule):
    """Оцінює розклад, повертаючи кількість конфліктів і штрафів."""
    logger.info("Оцінка розкладу...")
    conflicts = 0
    session = Session()
    try:
        # Групування слотів по часу
        slots_by_time = {}
        for slot in schedule:
            ts = slot["time_slot"]
            if ts not in slots_by_time:
                slots_by_time[ts] = []
            slots_by_time[ts].append(slot)

        # Відстеження зайнятості груп, підгруп і викладачів
        group_slots = {}
        subgroup_slots = {}
        teacher_load = {}
        group_day_counts = {g.id: {day: 0 for day in ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"]} for g in
                            load_data()["groups"]}
        teacher_availability = {t.id: json.loads(t.availability) for t in get_all_teachers()}
        classroom_capacity = {c.id: c.capacity for c in get_all_classrooms()}

        for ts, slots in slots_by_time.items():
            for i, slot1 in enumerate(slots):
                # Конфлікти груп
                if slot1.get("group_id"):
                    group_id = slot1["group_id"]
                    if group_id not in group_slots:
                        group_slots[group_id] = {}
                    if ts in group_slots[group_id]:
                        conflicts += 1
                    group_slots[group_id][ts] = group_slots[group_id].get(ts, 0) + 1

                # Конфлікти підгруп
                if slot1.get("subgroup_id"):
                    subgroup_id = slot1["subgroup_id"]
                    if subgroup_id not in subgroup_slots:
                        subgroup_slots[subgroup_id] = {}
                    if ts in subgroup_slots[subgroup_id]:
                        conflicts += 1
                    subgroup_slots[subgroup_id][ts] = subgroup_slots[subgroup_id].get(ts, 0) + 1

                # НОВА ПЕРЕВІРКА: Конфлікт між лекцією групи та лабораторною її підгрупи
                if slot1.get("group_id"):  # Якщо це лекція для групи
                    group_id = slot1["group_id"]
                    group_name = get_group_by_id(group_id).name if get_group_by_id(group_id) else "Unknown"
                    for slot2 in slots:
                        if slot2.get("subgroup_id"):  # Якщо є лабораторна для підгрупи
                            subgroup = get_subgroup_by_id(slot2["subgroup_id"])
                            if subgroup and subgroup.group_id == group_id:
                                conflicts += 2  # Штраф за конфлікт
                                subgroup_name = subgroup.name if subgroup else "Unknown"
                                logger.warning(
                                    f"Конфлікт: лекція для групи {group_name} (ID: {group_id}) "
                                    f"і лабораторна для підгрупи {subgroup_name} (ID: {slot2['subgroup_id']}) у {ts}"
                                )

                # Конфлікти викладачів і аудиторій
                for slot2 in slots[i + 1:]:
                    if slot1["teacher_id"] == slot2["teacher_id"]:
                        conflicts += 1
                    if slot1["classroom_id"] == slot2["classroom_id"]:
                        conflicts += 1
                    # Конфлікт між підгрупами однієї групи
                    if (
                        slot1.get("subgroup_id") and slot2.get("subgroup_id")
                        and slot1["subgroup_id"] != slot2["subgroup_id"]
                    ):
                        subgroup1 = get_subgroup_by_id(slot1["subgroup_id"])
                        subgroup2 = get_subgroup_by_id(slot2["subgroup_id"])
                        if subgroup1 and subgroup2 and subgroup1.group_id == subgroup2.group_id:
                            conflicts += 1

                # Перевірка навантаження викладача
                teacher_id = slot1["teacher_id"]
                teacher_load[teacher_id] = teacher_load.get(teacher_id, 0) + 1
                teacher = get_teacher_by_id(teacher_id)
                if teacher and teacher_load[teacher_id] > teacher.max_load:
                    conflicts += (teacher_load[teacher_id] - teacher.max_load) * 2

                # Перевірка доступності викладача
                if teacher_id in teacher_availability:
                    day, time = ts.split(" ", 1)
                    available_slots = teacher_availability[teacher_id].get(day, [])
                    if time not in available_slots:
                        conflicts += 2

                # Штраф за місткість і тип аудиторії
                classroom = get_classroom_by_id(slot1["classroom_id"])
                if classroom:
                    student_count = slot1["group_student_count"] if slot1["group_id"] else slot1["subgroup_student_count"]
                    if slot1["lesson_type"] == LessonType.LECTURE.value:
                        if classroom.type != ClassroomType.LECTURE or student_count > classroom_capacity[classroom.id]:
                            conflicts += 2
                    elif slot1["lesson_type"] == LessonType.LAB.value:
                        if classroom.type != ClassroomType.LAB or student_count > classroom_capacity[classroom.id] / 2:
                            conflicts += 2

                # Рівномірність розкладу для груп
                if slot1["group_id"]:
                    day = ts.split(" ")[0]
                    group_day_counts[slot1["group_id"]][day] += 1

            # Штраф за нерівномірний розподіл занять по днях
            for group_id, counts in group_day_counts.items():
                avg = sum(counts.values()) / len(counts)
                for count in counts.values():
                    if count > avg + 1:
                        conflicts += count

        # Штраф за відсутність дисциплін
        data = load_data()
        group_lectures = {g.id: set() for g in data["groups"]}
        subgroup_labs = {s.id: set() for s in data["subgroups"]}
        for slot in schedule:
            if slot["group_id"]:
                group_lectures[slot["group_id"]].add(slot["discipline_id"])
            elif slot["subgroup_id"]:
                subgroup_labs[slot["subgroup_id"]].add(slot["discipline_id"])

        for group in data["groups"]:
            missing_lectures = len(data["discipline_ids"]) - len(group_lectures.get(group.id, set()))
            conflicts += missing_lectures * 2
        for subgroup in data["subgroups"]:
            missing_labs = len(data["discipline_ids"]) - len(subgroup_labs.get(subgroup.id, set()))
            conflicts += missing_labs * 2

    finally:
        session.close()
    return conflicts

def perturb_schedule(schedule):
    """Створює сусідній розклад, змінюючи випадковий параметр одного слота."""
    logger.info("Створення сусіднього розкладу...")
    new_schedule = [slot.copy() for slot in schedule]
    idx = random.randint(0, len(new_schedule) - 1)
    slot = new_schedule[idx]
    data = load_data()

    change = random.choice(["teacher", "classroom", "time_slot"])
    if change == "teacher":
        teacher_ids = get_teachers_for_discipline(slot["discipline_id"])
        if teacher_ids:
            slot["teacher_id"] = random.choice(teacher_ids)
    elif change == "classroom":
        student_count = slot["group_student_count"] if slot["group_id"] else slot["subgroup_student_count"]
        suitable_classrooms = get_classrooms_by_type(
            ClassroomType.LECTURE if slot["lesson_type"] == LessonType.LECTURE.value else ClassroomType.LAB
        )
        suitable_classrooms = [c for c in suitable_classrooms if c.capacity >= student_count]
        if suitable_classrooms:
            slot["classroom_id"] = random.choice([c.id for c in suitable_classrooms])
    elif change == "time_slot":
        slot["time_slot"] = random.choice(data["time_slots"])

    return new_schedule

def run_simulated_annealing():
    """Запускає імітацію відпалу для оптимізації розкладу."""
    logger.info("Запуск імітації відпалу...")
    schedule_data = load_data()
    current_schedule = generate_initial_schedule()
    current_fitness = evaluate_schedule(current_schedule)

    # Параметри SA
    T = 1000.0  # Початкова температура
    T_min = 0.01  # Кінцева температура
    alpha = 0.995  # Коефіцієнт охолодження
    max_iterations = 10000  # Максимум ітерацій
    stagnation_limit = 2000  # Ліміт ітерацій без покращення
    stagnation_count = 0
    best_schedule = current_schedule[:]
    best_fitness = current_fitness

    iteration = 0
    while T > T_min and iteration < max_iterations:
        new_schedule = perturb_schedule(current_schedule)
        new_fitness = evaluate_schedule(new_schedule)

        delta = new_fitness - current_fitness
        if delta <= 0 or random.random() < math.exp(-delta / T):
            current_schedule = new_schedule
            current_fitness = new_fitness

        if new_fitness < best_fitness:
            best_schedule = new_schedule[:]
            best_fitness = new_fitness
            stagnation_count = 0
            logger.info(f"Ітерація {iteration}, Новий найкращий фітнес: {best_fitness}")
        else:
            stagnation_count += 1

        if stagnation_count > stagnation_limit:
            logger.info(f"Стагнація після {iteration} ітерацій")
            break

        T *= alpha
        iteration += 1

        if iteration % 2000 == 0:
            logger.info(f"Ітерація {iteration}, Конфлікти: {best_fitness}, Температура: {T:.2f}")

    # Збереження розкладу в базу
    session = Session()
    try:
        for slot in best_schedule:
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
    kn21_count = sum(1 for slot in best_schedule if slot.get("group_id") and
                     get_group_by_id(slot["group_id"]).name == "КН-21")
    logger.info(f"Оптимізація завершена. Конфлікти: {best_fitness}, Занять: {len(best_schedule)}")
    logger.info(f"Занять для КН-21: {kn21_count}")

    # Перевірка конфліктів
    time_slots = {}
    for slot in best_schedule:
        key = (slot.get("group_id"), slot.get("subgroup_id"), slot["time_slot"])
        time_slots[key] = time_slots.get(key, 0) + 1
        if time_slots[key] > 1:
            logger.warning(f"Конфлікт: {key} має {time_slots[key]} занять")

    # Дебаг-вивід фінального розкладу
    logger.info("Фінальний розклад:")
    for slot in best_schedule:
        group = get_group_by_id(slot["group_id"]).name if slot["group_id"] else "-"
        subgroup = get_subgroup_by_id(slot["subgroup_id"]).name if slot["subgroup_id"] else "-"
        logger.info(f"Група: {group}, Підгрупа: {subgroup}, Час: {slot['time_slot']}, Тип: {slot['lesson_type']}")

    return best_schedule

if __name__ == "__main__":
    try:
        best_schedule = run_simulated_annealing()
        logger.info("Найкращий розклад")
    except Exception as e:
        logger.error(f"Помилка: {e}")