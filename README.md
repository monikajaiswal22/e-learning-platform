# 🎓 E-Learning Platform

A full-featured E-Learning Platform built with Python Flask that provides courses, video lessons, quizzes, certificates, and separate portals for Admin, Instructor, and Student.

🔗 Live Demo: https://elearning-platform-xxxx.onrender.com *(deploy ke baad update karna)*

🔗 GitHub Repository: https://github.com/monikajaiswal22/e-learning-platform

---

## 📌 Project Overview

The **E-Learning Platform** is a web-based application designed to simplify online learning and course management from a single platform.

It provides role-based access for **administrators**, **instructors**, and **students**, with features for course creation, video lessons, interactive quizzes, certificate generation, wishlist, reviews, and more.

---

## ✨ Features

### 👨‍💼 Admin Dashboard
- Complete user management (create, edit, delete)
- Role assignment (student / instructor / admin)
- Platform-wide analytics and statistics
- Course moderation
- View all courses and enrollments

### 👨‍🏫 Instructor Dashboard
- Create and manage courses
- Upload course images
- Add video lessons (YouTube / Vimeo / MP4 support)
- Build interactive quizzes with multiple choice questions
- Track student progress and enrollments
- View course ratings and reviews
- Edit and delete courses

### 👨‍🎓 Student Portal
- Secure registration and login
- Browse courses by category, level, and price
- Filter and search courses
- Enroll in courses (free / paid)
- Watch video lessons with progress tracking
- Take quizzes with instant feedback
- Download completion certificates (PDF)
- Wishlist to save favorite courses
- Write reviews and ratings
- Personal dashboard with statistics
- Profile management with avatar upload

### 🔐 Role-Based Authentication
Separate access for:
- Admin
- Instructor
- Student

### 📜 Certificate Generation
- Auto-generated PDF certificates
- Professional gold-themed design
- Custom certificate ID
- Download as PDF

### 📊 Quiz System
- Multiple choice questions
- Instant score calculation
- 70% passing threshold
- Retake option
- Quiz performance tracking
- Leaderboard rankings

### 🌐 Public Website
- Homepage with featured courses
- Course catalog
- Contact page
- Leaderboard
- Search functionality

---

## 🛠️ Tech Stack

### Backend
- Python 3.11+
- Flask 2.3.3
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF
- ReportLab (PDF generation)
- python-dotenv

### Frontend
- HTML5
- CSS3 (Custom Crimson Red theme)
- Bootstrap 5
- Vanilla JavaScript
- Font Awesome icons
- Google Fonts (Inter, Plus Jakarta Sans)

### Database
- SQLite (development)

### Deployment
- Render

---

## 🔑 Demo Credentials

⚠️ These credentials are for demonstration purposes only.

### Admin
- Email: `admin@elearning.com`
- Password: `admin123`

### Instructor
- Email: `instructor@example.com`
- Password: `instructor123`

### Student
- Email: `student@example.com`
- Password: `student123`

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- pip
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/monikajaiswal22/e-learning-platform.git
cd e-learning-platform

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
cp .env.example .env
# Edit .env and set your SECRET_KEY

# 6. Initialize the database
flask init-db

# 7. Run the application
python app.py