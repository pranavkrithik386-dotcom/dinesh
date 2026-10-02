import os
import json
from datetime import datetime, date
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from groq import Groq

app = Flask(__name__, static_folder="frontend", static_url_path="")

DATA_FILE = Path("data.json")
MODEL = "openai/gpt-oss-20b"


# ============================================================
# DEFAULT DATABASE
# ============================================================

DEFAULT_DATA = {
    "settings": {
        "college_name": "",
        "student_name": "",
        "course": "",
        "year": "",
        "semester": "",
        "working_days": 6,
        "periods_per_day": 7,
        "period_duration": 50,
        "college_start_time": "08:30",
        "attendance_minimum": 75
    },

    "subjects": [],

    "timetable": [],

    "attendance": [],

    "assignments": [],

    "exams": [],

    "materials": [],

    "chat": []
}


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def load_data():
    if not DATA_FILE.exists():
        save_data(DEFAULT_DATA.copy())

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Make sure new sections exist if an old data.json is used
        for key, value in DEFAULT_DATA.items():
            if key not in data:
                data[key] = value

        return data

    except Exception:
        return DEFAULT_DATA.copy()


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def next_id(items):
    if not items:
        return 1

    ids = []

    for item in items:
        try:
            ids.append(int(item.get("id", 0)))
        except:
            pass

    return max(ids, default=0) + 1


def today_name():
    return datetime.now().strftime("%A")


def today_date():
    return datetime.now().strftime("%Y-%m-%d")


# ============================================================
# AI
# ============================================================

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return None

    return Groq(api_key=api_key)


def build_student_context(data):
    settings = data.get("settings", {})

    context = {
        "student": settings,
        "subjects": data.get("subjects", []),
        "timetable": data.get("timetable", []),
        "attendance": data.get("attendance", []),
        "assignments": data.get("assignments", []),
        "exams": data.get("exams", [])
    }

    return json.dumps(context, indent=2, ensure_ascii=False)


def build_ai_messages(user_message, data):
    recent_chat = data.get("chat", [])[-16:]

    system_prompt = f"""
You are SmartStudy AI, a friendly personal college study assistant.

You are NOT a textbook generator.
You are NOT supposed to dump huge answers unless the student explicitly asks for detail.

Talk naturally like a helpful tutor.

Important behavior:
- Answer the student's actual question first.
- Keep normal answers concise.
- Prefer short paragraphs and small bullet points.
- Do not create giant tables unless requested.
- Teach one concept at a time.
- If the student is confused, simplify the explanation.
- You can understand beginner English, spelling mistakes, and Tanglish.
- Do not repeatedly say "Sure!" or "Absolutely!".
- Ask at most ONE useful follow-up question when needed.
- If the student asks to learn programming, explain the concept, give a tiny example, then ask them to try.
- For C programming, assume beginner level unless the user says otherwise.
- For exam preparation, prioritize upcoming exams and unfinished assignments.
- If the user asks about attendance, use the student's stored attendance data.
- If the user asks about timetable, use the stored timetable.
- If information is missing, say what is missing instead of inventing it.
- Do not invent exam dates, attendance percentages, or assignments.
- If a user asks for a study plan, make it realistic and short.
- Voice-friendly answers are preferred.
- Be encouraging but not overly motivational.

CURRENT STUDENT DATA:
{build_student_context(data)}
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for item in recent_chat:
        role = item.get("role")

        if role in ["user", "assistant"]:
            messages.append({
                "role": role,
                "content": item.get("content", "")
            })

    messages.append({
        "role": "user",
        "content": user_message
    })

    return messages


def ask_ai(user_message, data):
    client = get_groq_client()

    if not client:
        return (
            "Your Groq API key is not configured yet. "
            "Set GROQ_API_KEY and restart the Flask server."
        )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=build_ai_messages(user_message, data),
            temperature=0.6,
            max_completion_tokens=900
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("Groq error:", e)
        return f"AI error: {str(e)}"


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def home():
    return send_from_directory("frontend", "index.html")


# ============================================================
# SETTINGS
# ============================================================

@app.get("/api/settings")
def get_settings():
    data = load_data()
    return jsonify(data["settings"])


@app.post("/api/settings")
def update_settings():
    data = load_data()
    body = request.get_json() or {}

    settings = data["settings"]

    for key in [
        "college_name",
        "student_name",
        "course",
        "year",
        "semester",
        "working_days",
        "periods_per_day",
        "period_duration",
        "college_start_time",
        "attendance_minimum"
    ]:
        if key in body:
            settings[key] = body[key]

    save_data(data)

    return jsonify({
        "success": True,
        "settings": settings
    })


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/api/dashboard")
def dashboard():
    data = load_data()

    attendance_summary = calculate_all_attendance(data)

    today = today_name()

    todays_classes = [
        x for x in data["timetable"]
        if x.get("day", "").lower() == today.lower()
    ]

    todays_classes.sort(
        key=lambda x: int(x.get("period", 0))
    )

    pending_assignments = [
        x for x in data["assignments"]
        if x.get("status", "Pending") != "Completed"
    ]

    upcoming_exams = get_upcoming_exams(data["exams"])

    return jsonify({
        "settings": data["settings"],
        "today": today,
        "today_date": today_date(),
        "todays_classes": todays_classes,
        "attendance": attendance_summary,
        "pending_assignments": pending_assignments,
        "upcoming_exams": upcoming_exams,
        "subjects": data["subjects"]
    })


# ============================================================
# SUBJECTS
# ============================================================

@app.get("/api/subjects")
def get_subjects():
    return jsonify(load_data()["subjects"])


@app.post("/api/subjects")
def add_subject():
    data = load_data()
    body = request.get_json() or {}

    name = str(body.get("name", "")).strip()

    if not name:
        return jsonify({"error": "Subject name is required"}), 400

    subject = {
        "id": next_id(data["subjects"]),
        "name": name,
        "code": body.get("code", ""),
        "teacher": body.get("teacher", ""),
        "room": body.get("room", "")
    }

    data["subjects"].append(subject)
    save_data(data)

    return jsonify(subject)


@app.delete("/api/subjects/<int:item_id>")
def delete_subject(item_id):
    data = load_data()

    data["subjects"] = [
        x for x in data["subjects"]
        if int(x.get("id", 0)) != item_id
    ]

    save_data(data)

    return jsonify({"success": True})


# ============================================================
# TIMETABLE
# ============================================================

@app.get("/api/timetable")
def get_timetable():
    data = load_data()

    timetable = sorted(
        data["timetable"],
        key=lambda x: (
            ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"].index(
                x.get("day", "Monday")
            ) if x.get("day") in [
                "Monday", "Tuesday", "Wednesday",
                "Thursday", "Friday", "Saturday", "Sunday"
            ] else 99,
            int(x.get("period", 0))
        )
    )

    return jsonify(timetable)


@app.post("/api/timetable")
def add_timetable():
    data = load_data()
    body = request.get_json() or {}

    item = {
        "id": next_id(data["timetable"]),
        "day": body.get("day", "Monday"),
        "period": int(body.get("period", 1)),
        "subject": body.get("subject", ""),
        "teacher": body.get("teacher", ""),
        "room": body.get("room", ""),
        "start_time": body.get("start_time", ""),
        "end_time": body.get("end_time", "")
    }

    data["timetable"].append(item)

    save_data(data)

    return jsonify(item)


@app.post("/api/timetable/bulk")
def bulk_timetable():
    data = load_data()
    body = request.get_json() or {}

    items = body.get("items", [])

    for item in items:
        item["id"] = next_id(data["timetable"])
        data["timetable"].append(item)

    save_data(data)

    return jsonify({
        "success": True,
        "added": len(items)
    })


@app.put("/api/timetable/<int:item_id>")
def update_timetable(item_id):
    data = load_data()
    body = request.get_json() or {}

    for item in data["timetable"]:
        if int(item.get("id", 0)) == item_id:
            item.update(body)
            break

    save_data(data)

    return jsonify({"success": True})


@app.delete("/api/timetable/<int:item_id>")
def delete_timetable(item_id):
    data = load_data()

    data["timetable"] = [
        x for x in data["timetable"]
        if int(x.get("id", 0)) != item_id
    ]

    save_data(data)

    return jsonify({"success": True})


# ============================================================
# ATTENDANCE
# ============================================================

def calculate_subject_attendance(data, subject):
    records = [
        x for x in data["attendance"]
        if x.get("subject", "").lower() == subject.lower()
    ]

    conducted = len(records)
    attended = len([
        x for x in records
        if x.get("status") == "Present"
    ])

    percentage = 0

    if conducted:
        percentage = round((attended / conducted) * 100, 1)

    return {
        "subject": subject,
        "attended": attended,
        "conducted": conducted,
        "percentage": percentage
    }


def calculate_all_attendance(data):
    subjects = [
        x.get("name")
        for x in data["subjects"]
    ]

    result = []

    for subject in subjects:
        result.append(
            calculate_subject_attendance(data, subject)
        )

    return result


@app.get("/api/attendance")
def get_attendance():
    data = load_data()

    return jsonify({
        "records": data["attendance"],
        "summary": calculate_all_attendance(data),
        "minimum": data["settings"].get("attendance_minimum", 75)
    })


@app.post("/api/attendance")
def add_attendance():
    data = load_data()
    body = request.get_json() or {}

    subject = body.get("subject", "").strip()

    if not subject:
        return jsonify({"error": "Subject is required"}), 400

    record = {
        "id": next_id(data["attendance"]),
        "date": body.get("date", today_date()),
        "day": body.get("day", today_name()),
        "period": int(body.get("period", 1)),
        "subject": subject,
        "status": body.get("status", "Present")
    }

    data["attendance"].append(record)

    save_data(data)

    return jsonify(record)


@app.post("/api/attendance/mark")
def mark_attendance():
    data = load_data()
    body = request.get_json() or {}

    record = {
        "id": next_id(data["attendance"]),
        "date": body.get("date", today_date()),
        "day": body.get("day", today_name()),
        "period": int(body.get("period", 1)),
        "subject": body.get("subject", ""),
        "status": body.get("status", "Present")
    }

    data["attendance"].append(record)
    save_data(data)

    return jsonify({
        "success": True,
        "record": record
    })


@app.delete("/api/attendance/<int:item_id>")
def delete_attendance(item_id):
    data = load_data()

    data["attendance"] = [
        x for x in data["attendance"]
        if int(x.get("id", 0)) != item_id
    ]

    save_data(data)

    return jsonify({"success": True})


@app.get("/api/attendance/calculate")
def attendance_calculate():
    data = load_data()

    subject = request.args.get("subject", "")
    target = float(
        request.args.get(
            "target",
            data["settings"].get("attendance_minimum", 75)
        )
    )

    result = calculate_subject_attendance(
        data,
        subject
    )

    attended = result["attended"]
    conducted = result["conducted"]

    current = result["percentage"]

    if conducted == 0:
        return jsonify({
            "subject": subject,
            "current": 0,
            "message": "No attendance records yet."
        })

    if current >= target:
        # Number of classes that can be missed
        can_miss = 0

        while True:
            new_conducted = conducted + can_miss + 1
            new_attended = attended

            if new_attended / new_conducted * 100 < target:
                break

            can_miss += 1

        return jsonify({
            "subject": subject,
            "current": current,
            "target": target,
            "can_miss": can_miss,
            "message": f"You can miss approximately {can_miss} more class(es) while staying at or above {target}%."
        })

    needed = 0

    while (
        attended + needed
    ) / (
        conducted + needed
    ) * 100 < target and needed < 10000:
        needed += 1

    return jsonify({
        "subject": subject,
        "current": current,
        "target": target,
        "classes_needed": needed,
        "message": f"You need to attend the next {needed} class(es) to reach {target}%."
    })


# ============================================================
# ASSIGNMENTS
# ============================================================

@app.get("/api/assignments")
def get_assignments():
    data = load_data()

    return jsonify(data["assignments"])


@app.post("/api/assignments")
def add_assignment():
    data = load_data()
    body = request.get_json() or {}

    assignment = {
        "id": next_id(data["assignments"]),
        "title": body.get("title", ""),
        "subject": body.get("subject", ""),
        "description": body.get("description", ""),
        "due_date": body.get("due_date", ""),
        "priority": body.get("priority", "Medium"),
        "status": body.get("status", "Pending"),
        "created_at": today_date()
    }

    data["assignments"].append(assignment)

    save_data(data)

    return jsonify(assignment)


@app.put("/api/assignments/<int:item_id>")
def update_assignment(item_id):
    data = load_data()
    body = request.get_json() or {}

    for item in data["assignments"]:
        if int(item.get("id", 0)) == item_id:
            item.update(body)
            break

    save_data(data)

    return jsonify({"success": True})


@app.delete("/api/assignments/<int:item_id>")
def delete_assignment(item_id):
    data = load_data()

    data["assignments"] = [
        x for x in data["assignments"]
        if int(x.get("id", 0)) != item_id
    ]

    save_data(data)

    return jsonify({"success": True})


# ============================================================
# EXAMS
# ============================================================

def get_upcoming_exams(exams):
    today = today_date()

    upcoming = [
        x for x in exams
        if x.get("date", "") >= today
    ]

    return sorted(
        upcoming,
        key=lambda x: x.get("date", "")
    )


@app.get("/api/exams")
def get_exams():
    data = load_data()

    return jsonify(data["exams"])


@app.post("/api/exams")
def add_exam():
    data = load_data()
    body = request.get_json() or {}

    exam = {
        "id": next_id(data["exams"]),
        "name": body.get("name", ""),
        "subject": body.get("subject", ""),
        "date": body.get("date", ""),
        "time": body.get("time", ""),
        "venue": body.get("venue", ""),
        "notes": body.get("notes", "")
    }

    data["exams"].append(exam)

    save_data(data)

    return jsonify(exam)


@app.put("/api/exams/<int:item_id>")
def update_exam(item_id):
    data = load_data()
    body = request.get_json() or {}

    for item in data["exams"]:
        if int(item.get("id", 0)) == item_id:
            item.update(body)
            break

    save_data(data)

    return jsonify({"success": True})


@app.delete("/api/exams/<int:item_id>")
def delete_exam(item_id):
    data = load_data()

    data["exams"] = [
        x for x in data["exams"]
        if int(x.get("id", 0)) != item_id
    ]

    save_data(data)

    return jsonify({"success": True})


# ============================================================
# MATERIALS
# ============================================================

@app.get("/api/materials")
def get_materials():
    return jsonify(load_data()["materials"])


@app.post("/api/materials")
def add_material():
    data = load_data()
    body = request.get_json() or {}

    material = {
        "id": next_id(data["materials"]),
        "name": body.get("name", ""),
        "subject": body.get("subject", ""),
        "type": body.get("type", "Note"),
        "url": body.get("url", ""),
        "created_at": today_date()
    }

    data["materials"].append(material)

    save_data(data)

    return jsonify(material)


@app.delete("/api/materials/<int:item_id>")
def delete_material(item_id):
    data = load_data()

    data["materials"] = [
        x for x in data["materials"]
        if int(x.get("id", 0)) != item_id
    ]

    save_data(data)

    return jsonify({"success": True})


# ============================================================
# AI CHAT
# ============================================================

@app.get("/api/chat")
def get_chat():
    return jsonify(load_data()["chat"])


@app.post("/api/chat")
def chat():
    data = load_data()
    body = request.get_json() or {}

    message = str(
        body.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "error": "Message is required"
        }), 400

    user_item = {
        "id": next_id(data["chat"]),
        "role": "user",
        "content": message,
        "time": datetime.now().isoformat()
    }

    data["chat"].append(user_item)

    answer = ask_ai(message, data)

    assistant_item = {
        "id": next_id(data["chat"]),
        "role": "assistant",
        "content": answer,
        "time": datetime.now().isoformat()
    }

    data["chat"].append(assistant_item)

    data["chat"] = data["chat"][-100:]

    save_data(data)

    return jsonify({
        "answer": answer
    })


@app.post("/api/chat/clear")
def clear_chat():
    data = load_data()

    data["chat"] = []

    save_data(data)

    return jsonify({
        "success": True
    })


# ============================================================
# AI STUDY PLAN
# ============================================================

@app.post("/api/ai/study-plan")
def ai_study_plan():
    data = load_data()

    prompt = """
Create a short realistic study plan for today based on my actual
timetable, assignments, exams and attendance.

Do not make a huge timetable.
Give me a simple priority order with approximate study durations.
Explain briefly why each task is important.
"""

    answer = ask_ai(prompt, data)

    return jsonify({
        "answer": answer
    })


# ============================================================
# AI MCQ
# ============================================================

@app.post("/api/ai/mcqs")
def ai_mcqs():
    data = load_data()
    body = request.get_json() or {}

    subject = body.get("subject", "C Programming")
    topic = body.get("topic", "")

    prompt = f"""
Give me ONE beginner-friendly multiple choice question.

Subject: {subject}
Topic: {topic}

Do not give 10 questions.
Give only ONE.

Format:

Question:
A)
B)
C)
D)

Wait for my answer.
"""

    answer = ask_ai(prompt, data)

    return jsonify({
        "answer": answer
    })


# ============================================================
# AI PROJECT HELP
# ============================================================

@app.post("/api/ai/project")
def ai_project():
    data = load_data()
    body = request.get_json() or {}

    project = body.get(
        "project",
        "student management system"
    )

    prompt = f"""
Help me with my college project:

{project}

Explain only the next useful step.
Do not dump a complete huge project unless I specifically ask.
"""

    answer = ask_ai(prompt, data)

    return jsonify({
        "answer": answer
    })


# ============================================================
# RESET DATA
# ============================================================

@app.post("/api/reset")
def reset_data():
    save_data(DEFAULT_DATA.copy())

    return jsonify({
        "success": True
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    print()
    print("=" * 55)
    print("          SMARTSTUDY AI")
    print("       COLLEGE STUDENT OS")
    print("=" * 55)
    print(f"Model: {MODEL}")
    print(
        "API KEY LOADED:",
        bool(os.getenv("GROQ_API_KEY"))
    )
    print("Open: http://127.0.0.1:5000")
    print("=" * 55)
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )