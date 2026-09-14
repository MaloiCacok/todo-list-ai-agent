from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for

import database

app = Flask(__name__)
app.secret_key = "super-secret-key-todo-app"

database.init_db()

PRIORITY_NAMES = {1: "Высокий", 2: "Средний", 3: "Низкий"}
WEEKDAYS = [
    "Понедельник", "Вторник", "Среда",
    "Четверг", "Пятница", "Суббота", "Воскресенье",
]


@app.template_filter("format_date")
def format_date(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(value)


def deadline_info(deadline_str):
    info = {"deadline_class": "", "deadline_label": "", "deadline_days": None}
    if not deadline_str:
        return info
    try:
        d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return info
    days = (d - datetime.now().date()).days
    info["deadline_days"] = days
    if days < 0:
        info["deadline_class"] = "overdue"
        info["deadline_label"] = f"Просрочен на {-days} дн."
    elif days == 0:
        info["deadline_class"] = "today"
        info["deadline_label"] = "Дедлайн сегодня!"
    elif days <= 2:
        info["deadline_class"] = "danger"
        info["deadline_label"] = f"Дедлайн через {days} дн."
    elif days <= 4:
        info["deadline_class"] = "warning"
        info["deadline_label"] = f"Дедлайн через {days} дн."
    else:
        info["deadline_class"] = "ok"
        info["deadline_label"] = f"Дедлайн через {days} дн."
    return info


def day_label(day):
    try:
        d = datetime.strptime(day, "%Y-%m-%d")
    except (ValueError, TypeError):
        return "Без даты"
    return f"{WEEKDAYS[d.weekday()]}, {d.strftime('%d.%m.%Y')}"


def valid_priority(value):
    try:
        priority = int(value)
    except (TypeError, ValueError):
        return None
    return priority if priority in (1, 2, 3) else None


def valid_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/add", methods=["GET", "POST"])
def add_task():
    today = datetime.now().strftime("%Y-%m-%d")
    form_data = {}

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        priority = valid_priority(request.form.get("priority"))
        raw_created = request.form.get("created_at", "").strip()
        raw_deadline = request.form.get("deadline", "").strip()
        description = request.form.get("description", "").strip()

        created_at = raw_created if valid_date(raw_created) else None
        deadline = raw_deadline if valid_date(raw_deadline) else None

        form_data = {
            "title": title,
            "priority": request.form.get("priority", ""),
            "created_at": created_at or today,
            "description": description,
            "deadline": deadline or "",
        }

        if not title:
            flash("Ошибка: название задачи не может быть пустым.", "error")
        elif priority is None:
            flash("Ошибка: приоритет должен быть 1 (высокий), 2 (средний) или 3 (низкий).", "error")
        elif raw_created and created_at is None:
            flash("Ошибка: некорректная дата создания.", "error")
        elif raw_deadline and deadline is None:
            flash("Ошибка: некорректная дата дедлайна.", "error")
        else:
            task_id = database.add_task(title, priority, created_at, description, deadline)
            flash(f"Задача #{task_id} успешно добавлена.", "success")
            return redirect(url_for("task_list"))

    return render_template(
        "add_task.html",
        priorities=PRIORITY_NAMES,
        today=today,
        form_data=form_data,
    )


@app.route("/task/<int:task_id>", methods=["GET", "POST"])
def task_detail(task_id):
    task = database.get_task(task_id)
    if task is None:
        flash(f"Ошибка: задача с номером {task_id} не существует.", "error")
        return redirect(url_for("task_list"))

    today = datetime.now().strftime("%Y-%m-%d")
    form_data = task.copy()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        priority = valid_priority(request.form.get("priority"))
        raw_created = request.form.get("created_at", "").strip()
        raw_deadline = request.form.get("deadline", "").strip()
        description = request.form.get("description", "").strip()

        created_at = raw_created if valid_date(raw_created) else None
        deadline = raw_deadline if valid_date(raw_deadline) else None

        form_data = {
            "title": title,
            "priority": request.form.get("priority", ""),
            "created_at": created_at or today,
            "description": description,
            "deadline": deadline or "",
        }

        if not title:
            flash("Ошибка: название задачи не может быть пустым.", "error")
        elif priority is None:
            flash("Ошибка: приоритет должен быть 1 (высокий), 2 (средний) или 3 (низкий).", "error")
        elif raw_created and created_at is None:
            flash("Ошибка: некорректная дата создания.", "error")
        elif raw_deadline and deadline is None:
            flash("Ошибка: некорректная дата дедлайна.", "error")
        else:
            database.update_task(task_id, title, priority, created_at, description, deadline)
            flash(f"Задача #{task_id} обновлена.", "success")
            return redirect(url_for("task_list"))

    return render_template(
        "task_detail.html",
        task=task,
        form_data=form_data,
        priorities=PRIORITY_NAMES,
        today=today,
    )


@app.route("/tasks")
def task_list():
    tasks = database.get_tasks()
    for task in tasks:
        task.update(deadline_info(task.get("deadline")))

    groups = {}
    for task in tasks:
        key = task.get("created_at") or "unknown"
        groups.setdefault(key, []).append(task)

    grouped = []
    for day in sorted(groups, key=lambda k: (k == "unknown", k or "")):
        items = sorted(groups[day], key=lambda t: (t["priority"], t["id"]))
        grouped.append({"date": day, "label": day_label(day), "tasks": items})

    return render_template(
        "task_list.html", groups=grouped, priorities=PRIORITY_NAMES
    )


@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    task = database.get_task(task_id)
    if task is None:
        flash(f"Ошибка: задача с номером {task_id} не существует.", "error")
    elif task["status"] == "Выполнено":
        flash(f"Задача #{task_id} уже выполнена.", "error")
    else:
        database.mark_complete(task_id)
        flash(f"Задача #{task_id} отмечена как выполненная.", "success")
    return redirect(url_for("task_list"))


@app.route("/reopen/<int:task_id>", methods=["POST"])
def reopen_task(task_id):
    task = database.get_task(task_id)
    if task is None:
        flash(f"Ошибка: задача с номером {task_id} не существует.", "error")
    elif task["status"] == "Не выполнено":
        flash(f"Задача #{task_id} уже не выполнена.", "error")
    else:
        database.mark_todo(task_id)
        flash(f"Задача #{task_id} возвращена в список невыполненных.", "success")
    return redirect(url_for("task_list"))


@app.route("/dashboard")
def dashboard():
    stats = database.get_stats()
    progress_data = database.get_progress_data()
    status_data = [
        {"label": "Выполнено", "value": stats["done"]},
        {"label": "Не выполнено", "value": stats["remaining"]},
    ]
    return render_template(
        "dashboard.html",
        stats=stats,
        progress_data=progress_data,
        status_data=status_data,
        priorities=PRIORITY_NAMES,
        chart_labels=list(PRIORITY_NAMES.keys()),
    )


if __name__ == "__main__":
    database.init_db()
    app.run(debug=True)