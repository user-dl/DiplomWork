import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QFormLayout, QDialog,
    QHBoxLayout, QLabel, QTabWidget, QLineEdit, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt
from optimization.algorithms.genetic import run_genetic_algorithm
from optimization.algorithms.simulated_annealing import run_simulated_annealing, evaluate_schedule
from optimization.algorithms.greedy import run_greedy_algorithm
from optimization.algorithms.random_search import run_random_search
from database.queries import (
    add_teacher, add_classroom, add_group, add_subgroup, add_discipline,
    get_discipline_by_id, get_teacher_by_id, get_classroom_by_id,
    get_group_by_id, get_subgroup_by_id, get_all_teachers, get_all_classrooms,
    get_all_groups, get_all_subgroups, get_all_disciplines, update_schedule,
    delete_teacher, delete_classroom, delete_group, delete_subgroup, delete_discipline,
    delete_schedule, get_teachers_for_discipline
)
from database.models import LessonType

class InputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Додати дані")
        layout = QFormLayout()

        self.teacher_name = QLineEdit()
        self.teacher_availability = QLineEdit('{"Понеділок": ["8:30-10:00", "10:00-11:30"], "Вівторок": ["8:30-10:00"]}')
        self.teacher_max_load = QLineEdit("10")
        self.classroom_number = QLineEdit()
        self.classroom_capacity = QLineEdit()
        self.classroom_type = QComboBox()
        self.classroom_type.addItems(["LECTURE", "LAB"])
        self.group_name = QLineEdit()
        self.group_student_count = QLineEdit()
        self.subgroup_name = QLineEdit()
        self.subgroup_student_count = QLineEdit()
        self.discipline_name = QLineEdit()

        layout.addRow("Ім'я викладача:", self.teacher_name)
        layout.addRow("Доступність (JSON):", self.teacher_availability)
        layout.addRow("Макс. навантаження:", self.teacher_max_load)
        layout.addRow("Номер аудиторії:", self.classroom_number)
        layout.addRow("Місткість аудиторії:", self.classroom_capacity)
        layout.addRow("Тип аудиторії:", self.classroom_type)
        layout.addRow("Назва групи:", self.group_name)
        layout.addRow("Кількість студентів у групі:", self.group_student_count)
        layout.addRow("Назва підгрупи:", self.subgroup_name)
        layout.addRow("Кількість студентів у підгрупі:", self.subgroup_student_count)
        layout.addRow("Назва дисципліни:", self.discipline_name)

        self.submit_button = QPushButton("Додати")
        self.submit_button.clicked.connect(self.submit)
        layout.addWidget(self.submit_button)

        self.setLayout(layout)

    def submit(self):
        try:
            if self.teacher_name.text():
                add_teacher(self.teacher_name.text(), self.teacher_availability.text(), int(self.teacher_max_load.text()))
            if self.classroom_number.text() and self.classroom_capacity.text():
                add_classroom(self.classroom_number.text(), int(self.classroom_capacity.text()), self.classroom_type.currentText())
            if self.group_name.text() and self.group_student_count.text():
                group_id = add_group(self.group_name.text(), int(self.group_student_count.text()))
                if self.subgroup_name.text() and self.subgroup_student_count.text():
                    add_subgroup(group_id, self.subgroup_name.text(), int(self.subgroup_student_count.text()))
            if self.discipline_name.text():
                add_discipline(self.discipline_name.text())
            self.accept()
        except ValueError as e:
            QMessageBox.critical(self, "Помилка", str(e))

class DeleteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Видалити дані")
        layout = QFormLayout()

        self.data_type = QComboBox()
        self.data_type.addItems(["Викладач", "Аудиторія", "Група", "Підгрупа", "Дисципліна", "Розклад"])
        self.data_type.currentTextChanged.connect(self.update_data_items)

        self.data_items = QComboBox()
        self.update_data_items(self.data_type.currentText())

        layout.addRow("Тип даних:", self.data_type)
        layout.addRow("Запис:", self.data_items)

        self.delete_button = QPushButton("Видалити")
        self.delete_button.clicked.connect(self.delete)
        layout.addWidget(self.delete_button)

        self.setLayout(layout)

    def update_data_items(self, data_type):
        self.data_items.clear()
        if data_type == "Викладач":
            items = [t.name for t in get_all_teachers()]
            ids = [t.id for t in get_all_teachers()]
        elif data_type == "Аудиторія":
            items = [c.number for c in get_all_classrooms()]
            ids = [c.id for c in get_all_classrooms()]
        elif data_type == "Група":
            items = [g.name for g in get_all_groups()]
            ids = [g.id for g in get_all_groups()]
        elif data_type == "Підгрупа":
            items = [s.name for s in get_all_subgroups()]
            ids = [s.id for s in get_all_subgroups()]
        elif data_type == "Дисципліна":
            items = [d.name for d in get_all_disciplines()]
            ids = [d.id for d in get_all_disciplines()]
        else:  # Розклад
            items = ["Увесь розклад"]
            ids = [None]
        self.data_items.addItems(items)
        self.data_items.setProperty("ids", ids)

    def delete(self):
        data_type = self.data_type.currentText()
        item_index = self.data_items.currentIndex()
        ids = self.data_items.property("ids")
        item_id = ids[item_index] if ids else None

        try:
            if data_type == "Викладач":
                delete_teacher(item_id)
            elif data_type == "Аудиторія":
                delete_classroom(item_id)
            elif data_type == "Група":
                delete_group(item_id)
            elif data_type == "Підгрупа":
                delete_subgroup(item_id)
            elif data_type == "Дисципліна":
                delete_discipline(item_id)
            elif data_type == "Розклад":
                delete_schedule()
            QMessageBox.information(self, "Успіх", f"Дані ({data_type}) успішно видалено")
            self.accept()
        except ValueError as e:
            QMessageBox.critical(self, "Помилка", str(e))

class ScheduleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Розклад занять")
        self.setGeometry(100, 100, 1200, 800)

        self.full_schedule = []
        self.schedule_ids = []
        self.time_slots = [
            "Понеділок 8:30-10:00", "Понеділок 10:00-11:30", "Понеділок 12:00-13:30", "Понеділок 13:30-15:00",
            "Вівторок 8:30-10:00", "Вівторок 10:00-11:30", "Вівторок 12:00-13:30", "Вівторок 13:30-15:00",
            "Середа 8:30-10:00", "Середа 10:00-11:30", "Середа 12:00-13:30", "Середа 13:30-15:00",
            "Четвер 8:30-10:00", "Четвер 10:00-11:30", "Четвер 12:00-13:30", "Четвер 13:30-15:00",
            "П'ятниця 8:30-10:00", "П'ятниця 10:00-11:30", "П'ятниця 12:00-13:30", "П'ятниця 13:30-15:00"
        ]
        self.days = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"]
        self.tables = {}

        layout = QVBoxLayout()

        # Кнопки
        button_layout = QHBoxLayout()
        self.button_input = QPushButton("Додати дані")
        self.button_input.clicked.connect(self.show_input_dialog)
        button_layout.addWidget(self.button_input)

        self.button_delete = QPushButton("Видалити дані")
        self.button_delete.clicked.connect(self.show_delete_dialog)
        button_layout.addWidget(self.button_delete)

        # Вибір алгоритму
        algorithm_label = QLabel("Алгоритм:")
        self.algorithm_choice = QComboBox()
        self.algorithm_choice.addItems(["Генетичний алгоритм", "Імітація відпалу", "Жадібний алгоритм", "Випадковий пошук"])
        button_layout.addWidget(algorithm_label)
        button_layout.addWidget(self.algorithm_choice)
        button_layout.addStretch()

        self.button_optimize = QPushButton("Запустити оптимізацію")
        self.button_optimize.clicked.connect(self.run_optimization)
        button_layout.addWidget(self.button_optimize)

        self.button_clear = QPushButton("Очистити розклад")
        self.button_clear.clicked.connect(self.clear_schedule)
        button_layout.addWidget(self.button_clear)

        self.button_export = QPushButton("Експортувати в CSV")
        self.button_export.clicked.connect(self.export_to_csv)
        button_layout.addWidget(self.button_export)

        layout.addLayout(button_layout)

        # Пошук і фільтри
        search_layout = QHBoxLayout()
        self.search_label = QLabel("Пошук (викладач/група):")
        self.search_input = QLineEdit()
        self.filter_type = QComboBox()
        self.filter_type.addItems(["Усі", "LECTURE", "LAB"])
        self.filter_discipline = QComboBox()
        self.filter_discipline.addItems(["Усі"] + [d.name for d in get_all_disciplines()])
        self.search_button = QPushButton("Пошук")
        self.search_button.clicked.connect(self.search_schedule)
        self.reset_button = QPushButton("Скинути")
        self.reset_button.clicked.connect(self.reset_schedule)
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(QLabel("Тип заняття:"))
        search_layout.addWidget(self.filter_type)
        search_layout.addWidget(QLabel("Дисципліна"))
        search_layout.addWidget(self.filter_discipline)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.reset_button)
        layout.addLayout(search_layout)

        # Вкладки
        self.tab_widget = QTabWidget()
        for day in self.days:
            table = QTableWidget()
            table.setRowCount(20)
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels([
                "Група/Підгрупа", "Викладач", "Аудиторія", "Дисципліна", "Тип", "Час"
            ])
            table.setColumnWidth(0, 150)
            table.setColumnWidth(1, 150)
            table.setColumnWidth(2, 100)
            table.setColumnWidth(3, 150)
            table.setColumnWidth(4, 100)
            table.setColumnWidth(5, 150)
            table.setEditTriggers(QTableWidget.DoubleClicked)
            table.cellChanged.connect(self.update_schedule)
            self.tables[day] = table
            self.tab_widget.addTab(table, day)
        layout.addWidget(self.tab_widget)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def show_input_dialog(self):
        dialog = InputDialog(self)
        dialog.exec_()

    def show_delete_dialog(self):
        dialog = DeleteDialog(self)
        dialog.exec_()

    def run_optimization(self):
        try:
            selected_algorithm = self.algorithm_choice.currentText()
            print(f"Вибрано алгоритм: {selected_algorithm}")

            # Вимірювання часу виконання
            start_time = time.time()

            if selected_algorithm == "Генетичний алгоритм":
                best_schedule = run_genetic_algorithm()
            elif selected_algorithm == "Імітація відпалу":
                best_schedule = run_simulated_annealing()
            elif selected_algorithm == "Жадібний алгоритм":
                best_schedule = run_greedy_algorithm()
            else:  # Випадковий пошук
                best_schedule = run_random_search()

            # Час виконання
            execution_time = time.time() - start_time

            self.full_schedule = best_schedule
            self.schedule_ids = [None] * len(best_schedule)
            self.display_schedule(best_schedule)
            conflicts = evaluate_schedule(best_schedule)
            QMessageBox.information(
                self, "Результат",
                f"Розклад згенеровано:\n"
                f"Алгоритм: {selected_algorithm}\n"
                f"Занять: {len(best_schedule)}\n"
                f"Конфліктів: {conflicts}\n"
                f"Час виконання: {execution_time:.2f} секунд"
            )
            print(f"Отримано розклад: {len(best_schedule)} занять, конфліктів: {conflicts}, "
                  f"час виконання: {execution_time:.2f} секунд")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Помилка оптимізації: {e}")

    def clear_schedule(self):
        """Очищає розклад із бази даних і GUI."""
        try:
            delete_schedule()
            self.full_schedule = []
            self.schedule_ids = []
            self.display_schedule([])
            QMessageBox.information(self, "Успіх", "Розклад очищено")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Помилка очищення розкладу: {e}")

    def display_schedule(self, schedule):
        for day in self.days:
            self.tables[day].setRowCount(0)
            self.tables[day].blockSignals(True)

        schedule_by_day = {day: [] for day in self.days}
        for slot in schedule:
            day = slot["time_slot"].split(" ")[0]
            if day in schedule_by_day:
                schedule_by_day[day].append(slot)

        time_order = {
            "8:30-10:00": 4,
            "10:00-11:30": 3,
            "12:00-13:30": 2,
            "13:30-15:00": 1
        }
        for day in self.days:
            table = self.tables[day]
            day_schedule = sorted(schedule_by_day[day], key=lambda slot: time_order.get(slot["time_slot"].split(" ")[1], 5))
            table.setRowCount(len(day_schedule))

            for row, slot in enumerate(day_schedule):
                group_or_subgroup = (get_group_by_id(slot["group_id"]).name if slot["group_id"]
                                     else get_subgroup_by_id(slot["subgroup_id"]).name if slot["subgroup_id"] else "")
                teacher = get_teacher_by_id(slot["teacher_id"]).name if get_teacher_by_id(slot["teacher_id"]) else ""
                classroom = get_classroom_by_id(slot["classroom_id"]).number if get_classroom_by_id(slot["classroom_id"]) else ""
                discipline = get_discipline_by_id(slot["discipline_id"]).name if get_discipline_by_id(slot["discipline_id"]) else ""

                table.setItem(row, 0, QTableWidgetItem(group_or_subgroup))
                table.setItem(row, 1, QTableWidgetItem(teacher))
                table.setItem(row, 2, QTableWidgetItem(classroom))
                table.setItem(row, 3, QTableWidgetItem(discipline))
                table.setItem(row, 4, QTableWidgetItem(slot["lesson_type"]))
                table.setItem(row, 5, QTableWidgetItem(slot["time_slot"]))
                table.item(row, 0).setFlags(Qt.ItemIsEnabled)

            table.blockSignals(False)

    def search_schedule(self):
        search_text = self.search_input.text().strip().lower()
        filter_type = self.filter_type.currentText()
        filter_disc = self.filter_discipline.currentText()

        filtered_schedule = []
        for slot in self.full_schedule:
            group_name = (get_group_by_id(slot["group_id"]).name.lower() if slot["group_id"]
                          else get_subgroup_by_id(slot["subgroup_id"]).name.lower() if slot["subgroup_id"] else "")
            teacher_name = get_teacher_by_id(slot["teacher_id"]).name.lower() if get_teacher_by_id(slot["teacher_id"]) else ""
            discipline_name = get_discipline_by_id(slot["discipline_id"]).name if get_discipline_by_id(slot["discipline_id"]) else ""

            if (not search_text or search_text in group_name or search_text in teacher_name) and \
               (filter_type == "Усі" or slot["lesson_type"] == filter_type) and \
               (filter_disc == "Усі" or discipline_name == filter_disc):
                filtered_schedule.append(slot)
        self.display_schedule(filtered_schedule)

    def reset_schedule(self):
        self.search_input.clear()
        self.filter_type.setCurrentText("Усі")
        self.filter_discipline.setCurrentText("Усі")
        self.display_schedule(self.full_schedule)

    def export_to_csv(self):
        import csv
        try:
            with open("schedule.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Група/Підгрупа", "Викладач", "Аудиторія", "Дисципліна", "Тип заняття", "Час"])
                for slot in self.full_schedule:
                    group_or_subgroup = (get_group_by_id(slot["group_id"]).name if slot["group_id"]
                                         else get_subgroup_by_id(slot["subgroup_id"]).name)
                    teacher = get_teacher_by_id(slot["teacher_id"]).name
                    classroom = get_classroom_by_id(slot["classroom_id"]).number
                    discipline = get_discipline_by_id(slot["discipline_id"]).name
                    writer.writerow([group_or_subgroup, teacher, classroom, discipline, slot["lesson_type"], slot["time_slot"]])
            QMessageBox.information(self, "Успіх", "Розклад експортовано в schedule.csv")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Помилка експорту: {e}")

    def update_schedule(self, row, column):
        day = self.tab_widget.tabText(self.tab_widget.currentIndex())
        table = self.tables[day]
        item = table.item(row, column)
        if not item:
            return

        value = item.text()
        slot_index = sum(self.tables[d].rowCount() for d in self.days[:self.days.index(day)]) + row
        if slot_index >= len(self.full_schedule):
            return

        slot = self.full_schedule[slot_index]
        try:
            if column == 1:  # Викладач
                teacher = next(t for t in get_all_teachers() if t.name == value)
                if teacher.id not in get_teachers_for_discipline(slot["discipline_id"]):
                    raise ValueError(f"{value} не викладає цю дисципліну")
                slot["teacher_id"] = teacher.id
            elif column == 2:  # Аудиторія
                classroom = next(c for c in get_all_classrooms() if c.number == value)
                slot["classroom_id"] = classroom.id
            elif column == 4:  # Тип
                if value not in [LessonType.LECTURE.value, LessonType.LAB.value]:
                    raise ValueError("Тип: LECTURE або LAB")
                slot["lesson_type"] = value
            elif column == 5:  # Час
                if not any(value in ts for ts in self.time_slots):
                    raise ValueError("Неправильний часовий слот")
                slot["time_slot"] = f"{day} {value}"

            if self.schedule_ids[slot_index]:
                update_schedule(
                    self.schedule_ids[slot_index],
                    teacher_id=slot["teacher_id"],
                    classroom_id=slot["classroom_id"],
                    lesson_type=slot["lesson_type"],
                    time_slot=slot["time_slot"]
                )
        except Exception as e:
            QMessageBox.critical(self, "Помилка", str(e))
            self.display_schedule(self.full_schedule)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Спрощені QSS-стилі
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f0f0;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            padding: 8px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton#button_delete, QPushButton#button_clear {
            background-color: #f44336;
        }
        QPushButton#button_delete:hover, QPushButton#button_clear:hover {
            background-color: #da190b;
        }
        QLineEdit, QComboBox {
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        QTableWidget {
            background-color: white;
            border: 1px solid #ccc;
        }
        QHeaderView::section {
            background-color: #4CAF50;
            color: white;
            padding: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #ccc;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            padding: 8px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #4CAF50;
            color: white;
        }
    """)

    window = ScheduleApp()
    window.show()
    sys.exit(app.exec_())