import random
import json
import logging
from deap import base, creator, tools, algorithms
from database.queries import (
    get_teacher_by_id, get_classroom_by_id, get_subgroup_by_id, get_discipline_by_id, get_teachers_for_discipline,
    Session, add_schedule
)
from database.models import Group, Subgroup, Teacher, Classroom, Discipline, LessonType, ClassroomType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)


def load_data():
    logger.info("Завантаження даних із бази...")
    session = Session()
    try:
        groups = session.query(Group).all()
        subgroups = session.query(Subgroup).all()
        teachers = session.query(Teacher).all()
        classrooms = session.query(Classroom).all()
        disciplines = session.query(Discipline).all()

        logger.info(
            f"Знайдено: груп={len(groups)}, підгруп={len(subgroups)}, викладачів={len(teachers)}, аудиторій={len(classrooms)}, дисциплін={len(disciplines)}")

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


def evaluate_schedule(individual):
    logger.info("Оцінка розкладу...")
    conflicts = 0
    session = Session()
    try:
        slots_by_time = {}
        for slot in individual:
            ts = slot["time_slot"]
            if ts not in slots_by_time:
                slots_by_time[ts] = []
            slots_by_time[ts].append(slot)

        group_slots = {}
        subgroup_slots = {}
        teacher_load = {}
        group_day_counts = {g.id: {day: 0 for day in ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"]} for g in
                            load_data()["groups"]}
        teacher_day_slots = {t.id: {day: [] for day in ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"]} for t
                             in session.query(Teacher).all()}

        for ts, slots in slots_by_time.items():
            for i, slot1 in enumerate(slots):
                if slot1.get("group_id"):
                    group_id = slot1["group_id"]
                    if group_id not in group_slots:
                        group_slots[group_id] = {}
                    group_slots[group_id][ts] = group_slots[group_id].get(ts, 0) + 1
                    if group_slots[group_id][ts] > 1:
                        conflicts += 10
                if slot1.get("subgroup_id"):
                    subgroup_id = slot1["subgroup_id"]
                    if subgroup_id not in subgroup_slots:
                        subgroup_slots[subgroup_id] = {}
                    subgroup_slots[subgroup_id][ts] = subgroup_slots[subgroup_id].get(ts, 0) + 1
                    if subgroup_slots[subgroup_id][ts] > 1:
                        conflicts += 10

                for slot2 in slots[i + 1:]:
                    if slot1["classroom_id"] == slot2["classroom_id"]:
                        conflicts += 1
                    if slot1["teacher_id"] == slot2["teacher_id"]:
                        conflicts += 1
                    if (
                            slot1.get("subgroup_id") and slot2.get("subgroup_id")
                            and slot1["subgroup_id"] != slot2["subgroup_id"]
                    ):
                        subgroup1 = session.query(Subgroup).filter_by(id=slot1["subgroup_id"]).first()
                        subgroup2 = session.query(Subgroup).filter_by(id=slot2["subgroup_id"]).first()
                        if subgroup1 and subgroup2 and subgroup1.group_id == subgroup2.group_id:
                            conflicts += 1

                teacher_id = slot1["teacher_id"]
                teacher_load[teacher_id] = teacher_load.get(teacher_id, 0) + 1
                teacher = get_teacher_by_id(teacher_id)
                if teacher and teacher_load[teacher_id] > teacher.max_load:
                    conflicts += (teacher_load[teacher_id] - teacher.max_load) * 10

                if teacher:
                    availability = json.loads(teacher.availability)
                    day, time = ts.split(" ", 1)
                    if day not in availability or time not in availability[day]:
                        conflicts += 1

                classroom = get_classroom_by_id(slot1["classroom_id"])
                if classroom:
                    student_count = slot1.get("subgroup_student_count", 0) if slot1.get("subgroup_id") else slot1.get(
                        "group_student_count", 0)
                    if slot1["lesson_type"] == LessonType.LAB.value:
                        if classroom.type != ClassroomType.LAB or student_count > classroom.capacity / 2:
                            conflicts += 5
                    elif slot1["lesson_type"] == LessonType.LECTURE.value:
                        if classroom.type != ClassroomType.LECTURE or student_count > classroom.capacity:
                            conflicts += 5

                if slot1.get("group_id"):
                    day = ts.split(" ")[0]
                    group_day_counts[slot1["group_id"]][day] += 1
                teacher_day_slots[teacher_id][ts.split(" ")[0]].append(ts)

                if slot1["lesson_type"] == LessonType.LECTURE.value and any(t in ts for t in ["12:00", "13:30"]):
                    conflicts += 2

            for group_id, counts in group_day_counts.items():
                avg = sum(counts.values()) / len(counts)
                for count in counts.values():
                    if count > avg + 1:
                        conflicts += (count - avg) * 5

            for teacher_id, days in teacher_day_slots.items():
                for day, slots in days.items():
                    if len(slots) > 1:
                        slot_indices = [load_data()["time_slots"].index(s) % 4 for s in slots]
                        if max(slot_indices) - min(slot_indices) + 1 > len(slots):
                            conflicts += 5

        data = load_data()
        group_lectures = {g.id: set() for g in data["groups"]}
        subgroup_labs = {s.id: set() for s in data["subgroups"]}
        for slot in individual:
            if slot["group_id"]:
                group_lectures[slot["group_id"]].add(slot["discipline_id"])
            elif slot["subgroup_id"]:
                subgroup_labs[slot["subgroup_id"]].add(slot["discipline_id"])

        for group in data["groups"]:
            missing_lectures = len(data["discipline_ids"]) - len(group_lectures.get(group.id, set()))
            conflicts += missing_lectures * 10
        for subgroup in data["subgroups"]:
            missing_labs = len(data["discipline_ids"]) - len(subgroup_labs.get(subgroup.id, set()))
            conflicts += missing_labs * 10
    finally:
        session.close()
    return conflicts,


def generate_slot(data, group=None, subgroup=None, discipline_id=None, lesson_type=None):
    if lesson_type == LessonType.LECTURE.value:
        group_id = group.id
        subgroup_id = None
        student_count = group.student_count
    else:
        group_id = None
        subgroup_id = subgroup.id
        student_count = subgroup.student_count

    teacher_ids = get_teachers_for_discipline(discipline_id)
    teacher_id = random.choice(teacher_ids) if teacher_ids else random.choice(data["teacher_ids"])

    session = Session()
    try:
        suitable_classrooms = session.query(Classroom).filter(
            Classroom.type == (ClassroomType.LECTURE if lesson_type == LessonType.LECTURE.value else ClassroomType.LAB),
            Classroom.capacity >= student_count
        ).all()
        classroom_id = random.choice([c.id for c in suitable_classrooms]) if suitable_classrooms else random.choice(
            data["classroom_ids"])
    finally:
        session.close()

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


def generate_individual():
    logger.info("Генерація індивіда...")
    data = load_data()
    individual = creator.Individual()

    for group in data["groups"]:
        for discipline_id in data["discipline_ids"]:
            lecture_slot = generate_slot(data, group=group, discipline_id=discipline_id,
                                         lesson_type=LessonType.LECTURE.value)
            individual.append(lecture_slot)

        subgroups = [s for s in data["subgroups"] if s.group_id == group.id]
        if len(subgroups) < 2:
            logger.warning(f"Група {group.name} має менше 2 підгруп!")
            continue
        for subgroup in subgroups:
            for discipline_id in data["discipline_ids"]:
                lab_slot = generate_slot(data, subgroup=subgroup, discipline_id=discipline_id,
                                         lesson_type=LessonType.LAB.value)
                individual.append(lab_slot)

    logger.info(f"Згенеровано {len(individual)} занять")
    return individual


toolbox = base.Toolbox()
toolbox.register("individual", generate_individual)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("evaluate", evaluate_schedule)
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.15)
toolbox.register("select", tools.selTournament, tournsize=3)


def run_genetic_algorithm():
    logger.info("Запуск генетичного алгоритму...")
    population = toolbox.population(n=100)

    for ind in population:
        ind.fitness.values = evaluate_schedule(ind)

    best_fitness = float("inf")
    no_improvement = 0
    for gen in range(100):
        logger.info(f"Покоління {gen + 1}/100")

        offspring = toolbox.select(population, len(population))
        offspring = list(map(toolbox.clone, offspring))

        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < 0.7:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values

        for mutant in offspring:
            if random.random() < 0.3:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fits = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fits):
            ind.fitness.values = fit

        population[:] = offspring

        current_best = min(ind.fitness.values[0] for ind in population)
        if current_best < best_fitness:
            best_fitness = current_best
            no_improvement = 0
        else:
            no_improvement += 1
        if no_improvement >= 20:
            logger.info("Зупинка: немає покращення фітнесу")
            break

    best = tools.selBest(population, k=1)[0]

    session = Session()
    try:
        for slot in best:
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
    finally:
        session.close()

    kn21_count = sum(1 for slot in best if slot.get("group_id") == 1 or slot.get("subgroup_id") in [1, 2])
    logger.info(f"Занять для КН-21: {kn21_count}")

    time_slots = {}
    for slot in best:
        key = (slot.get("group_id"), slot.get("subgroup_id"), slot["time_slot"])
        time_slots[key] = time_slots.get(key, 0) + 1
        if time_slots[key] > 1:
            logger.warning(f"Конфлікт: {key} має {time_slots[key]} занять")

    return best


if __name__ == "__main__":
    try:
        best_schedule = run_genetic_algorithm()
        print("Найкращий розклад:", best_schedule)
    except Exception as e:
        logger.error(f"Помилка: {e}")