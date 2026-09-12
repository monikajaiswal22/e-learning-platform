# 🎓 E-Learning Platform

A full-featured E-Learning Platform built with Flask.

## ✨ Features

- User authentication (student, instructor, admin)
- Course management with video lessons
- Interactive quizzes with instant feedback
- PDF certificate generation
- Wishlist and reviews
- Complete admin panel

## 🛠 Tech Stack

- Flask 2.3.3
- SQLAlchemy
- Flask-Login
- Bootstrap 5
- SQLite
- ReportLab

## 🚀 Installation

```bash
git clone https://github.com/monikajaiswal22/elearning-platform.git
cd elearning-platform

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

# Create .env file with SECRET_KEY
flask init-db
python app.py