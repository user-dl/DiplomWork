from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)

# Шлях до schedule.csv у директорії desktop_app
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "desktop_app", "schedule.csv")
print(f"Шлях до schedule.csv: {CSV_PATH}")

def load_schedule():
    """Завантажує розклад із schedule.csv."""
    try:
        if not os.path.exists(CSV_PATH):
            print(f"Файл не знайдено: {CSV_PATH}")
            return []
        df = pd.read_csv(CSV_PATH, encoding="utf-8")
        expected_columns = ["Група/Підгрупа", "Викладач", "Аудиторія", "Дисципліна", "Тип заняття", "Час"]
        if not all(col in df.columns for col in expected_columns):
            print(f"Неправильний формат CSV. Очікувані колонки: {expected_columns}")
            return []
        print(f"Файл успішно прочитано, записів: {len(df)}")
        return df.to_dict("records")
    except Exception as e:
        print(f"Помилка читання schedule.csv: {e}")
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    """Відображає розклад і обробляє пошук, фільтри та сортування."""
    schedule = load_schedule()
    filtered_schedule = schedule

    # Статистика
    stats = {
        "total_lessons": len(schedule),
        "lectures": sum(1 for s in schedule if s["Тип заняття"] == "LECTURE"),
        "labs": sum(1 for s in schedule if s["Тип заняття"] == "LAB")
    }

    # Сортування
    sort_by = request.args.get("sort_by", "Час")
    if sort_by in ["Група/Підгрупа", "Викладач", "Аудиторія", "Дисципліна", "Тип заняття", "Час"]:
        filtered_schedule = sorted(filtered_schedule, key=lambda x: str(x[sort_by]).lower())

    if request.method == "POST":
        search_query = request.form.get("search_query", "").strip().lower()
        search_field = request.form.get("search_field", "all")
        day_filter = request.form.get("day_filter", "all")

        # Мапінг англомовних значень на українські для фільтрації
        day_mapping = {
            "Monday": "Понеділок",
            "Tuesday": "Вівторок",
            "Wednesday": "Середа",
            "Thursday": "Четвер",
            "Friday": "П'ятниця"
        }

        if search_query or day_filter != "all":
            filtered_schedule = []
            for slot in schedule:
                matches_search = True
                matches_day = True

                # Пошук
                if search_query:
                    if search_field == "all":
                        matches_search = (
                            search_query in str(slot["Група/Підгрупа"]).lower() or
                            search_query in str(slot["Викладач"]).lower() or
                            search_query in str(slot["Аудиторія"]).lower() or
                            search_query in str(slot["Дисципліна"]).lower()
                        )
                    elif search_field == "teacher":
                        matches_search = search_query in str(slot["Викладач"]).lower()
                    elif search_field == "group":
                        matches_search = search_query in str(slot["Група/Підгрупа"]).lower()
                    elif search_field == "discipline":
                        matches_search = search_query in str(slot["Дисципліна"]).lower()
                    elif search_field == "classroom":
                        matches_search = search_query in str(slot["Аудиторія"]).lower()

                # Фільтр за днем
                if day_filter != "all":
                    ukr_day = day_mapping.get(day_filter, "")
                    matches_day = ukr_day and slot["Час"].startswith(ukr_day)

                if matches_search and matches_day:
                    filtered_schedule.append(slot)

        # Повторне сортування після фільтрації
        if sort_by in ["Група/Підгрупа", "Викладач", "Аудиторія", "Дисципліна", "Тип заняття", "Час"]:
            filtered_schedule = sorted(filtered_schedule, key=lambda x: str(x[sort_by]).lower())

    return render_template("index.html", schedule=filtered_schedule, stats=stats, sort_by=sort_by)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)