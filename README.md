# SmartStudy AI — Generative AI Student Automation

## Technology
- Python
- Flask
- Groq API
- `openai/gpt-oss-20b`
- HTML/CSS/JavaScript frontend served by Python
- JSON local storage

No Node.js or npm is required.

## Features

### Generative AI
Students can ask their own questions:
- Subject doubts
- C/Python/Java/C++ programming
- Exam preparation
- Personalized study plans
- MCQ generation
- Assignment help
- Project guidance
- Concept explanations
- Revision plans

The AI receives relevant stored student context: subjects, attendance, timetable, exams and assignments.

### Student Automation
- Student-entered subjects
- Daily attendance
- Present → adds the number of classes entered for that day
- Daily timetable
- Exam date + subject + exam count
- Assignment/project tracker

## Run in VS Code

### 1. Open the extracted folder

Open `smartstudy_ai_groq_python` in VS Code.

### 2. Create a virtual environment

```bash
python -m venv venv
```

Windows activation:

```bash
venv\Scripts\activate
```

### 3. Install packages

```bash
pip install -r requirements.txt
```

### 4. Add your Groq API key

Windows CMD:

```bash
set GROQ_API_KEY=YOUR_GROQ_API_KEY
```

PowerShell:

```powershell
$env:GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

### 5. Start the application

```bash
python app.py
```

### 6. Open the website

```text
http://127.0.0.1:5000
```

## GenAI Flow

Student Question
→ Python Flask
→ Groq API
→ `openai/gpt-oss-20b`
→ Generated personalized answer

## Hackathon Description

**SmartStudy AI** is a Generative AI-powered student assistant that combines academic automation with an AI tutor.

Students enter their subjects, attendance, timetable, exams and project information. They can then ask natural-language questions. The AI generates personalized explanations, study plans, MCQs, exam preparation and project guidance using the student's context.

## Security

Never put your real API key in `app.py`.
Never upload your API key to GitHub.
Use the `GROQ_API_KEY` environment variable.

## Project Structure

```text
smartstudy_ai_groq_python/
├── app.py
├── requirements.txt
├── data.json
├── .env.example
├── .gitignore
├── README.md
└── frontend/
    └── index.html
```
