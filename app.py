# app.py
import os
import uuid
import io
import logging
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for, flash, request,
    send_from_directory, make_response, jsonify
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from dotenv import load_dotenv
load_dotenv()  # .env file load karo

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from models import (
    db, User, Course, Lesson, Enrollment, UserActivity, LessonProgress,
    Review, Wishlist, Quiz, QuizAttempt
)
from forms import (
    RegistrationForm, LoginForm, CourseForm, LessonForm, ProfileForm, AvatarForm,
    ReviewForm, ContactForm, SearchForm, NewsletterForm, PasswordChangeForm,
    PasswordResetRequestForm, PasswordResetForm, QuizForm, CourseFilterForm,
    AdminUserForm, CertificateForm
)

# ==================== CONFIG ====================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
INSTANCE_FOLDER = os.path.join(BASE_DIR, 'instance')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure required folders exist 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INSTANCE_FOLDER, exist_ok=True)

app = Flask(__name__)

# SECRET_KEY from env (mandatory)
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise ValueError(
        "SECRET_KEY environment variable not set! "
        "Create a .env file with SECRET_KEY=your-random-secret"
    )
app.config['SECRET_KEY'] = secret_key

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    f'sqlite:///{os.path.join(INSTANCE_FOLDER, "elearning.db")}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== EXTENSIONS ====================

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== DECORATORS ====================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== CLI COMMAND: INIT DB ====================

@app.cli.command("init-db")
def init_db_command():
    """Initialize database and create default users.
    Usage: flask init-db
    """
    db.create_all()

    admin = User.query.filter_by(email='admin@elearning.com').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@elearning.com',
            password=generate_password_hash('admin123'),
            full_name='System Administrator',
            is_instructor=True,
            is_admin=True
        )
        db.session.add(admin)
        logger.info("Admin user created: admin@elearning.com / admin123")

    demo_instructor = User.query.filter_by(email='instructor@example.com').first()
    if not demo_instructor:
        demo_instructor = User(
            username='demoinstructor',
            email='instructor@example.com',
            password=generate_password_hash('instructor123'),
            full_name='Demo Instructor',
            bio='Experienced educator passionate about teaching',
            is_instructor=True,
            is_admin=False
        )
        db.session.add(demo_instructor)
        logger.info("Demo instructor created: instructor@example.com / instructor123")

    demo_student = User.query.filter_by(email='student@example.com').first()
    if not demo_student:
        demo_student = User(
            username='demostudent',
            email='student@example.com',
            password=generate_password_hash('student123'),
            full_name='Demo Student',
            bio='Eager learner ready to explore new courses',
            is_instructor=False,
            is_admin=False
        )
        db.session.add(demo_student)
        logger.info("Demo student created: student@example.com / student123")

    db.session.commit()
    logger.info("Database initialized successfully.")


# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def utility_processor():
    def get_course_count():
        return Course.query.count()

    def get_user_count():
        return User.query.count()

    def get_current_year():
        return datetime.now().year

    def get_unread_notifications():
        return 0

    def get_categories():
        return [
            ('programming', 'Programming'),
            ('webdev', 'Web Development'),
            ('business', 'Business'),
            ('design', 'Design'),
            ('datascience', 'Data Science'),
            ('marketing', 'Marketing'),
            ('photography', 'Photography'),
            ('music', 'Music'),
            ('language', 'Language Learning'),
            ('other', 'Other')
        ]

    return dict(
        get_course_count=get_course_count,
        get_user_count=get_user_count,
        get_current_year=get_current_year,
        get_unread_notifications=get_unread_notifications,
        get_categories=get_categories,
        now=datetime.now()
    )


# ==================== MAIN ROUTES ====================

@app.route('/')
def index():
    featured_courses = Course.query.order_by(Course.created_at.desc()).limit(6).all()
    all_courses = Course.query.all()
    popular_courses = sorted(all_courses, key=lambda c: c.enrollments.count(), reverse=True)[:6]
    top_instructors = User.query.filter_by(is_instructor=True).limit(4).all()
    free_courses = Course.query.filter_by(price=0).limit(3).all()

    return render_template(
        'index.html',
        featured_courses=featured_courses,
        popular_courses=popular_courses,
        courses=featured_courses,
        top_instructors=top_instructors,
        free_courses=free_courses
    )


# ==================== AUTH ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already registered.', 'danger')
                return render_template('register.html', form=form)

            if User.query.filter_by(username=form.username.data).first():
                flash('Username already taken.', 'danger')
                return render_template('register.html', form=form)

            hashed_password = generate_password_hash(form.password.data)

            # instructor flag from form — but user is NOT auto-approved
            requested_instructor = bool(
                getattr(form, 'is_instructor', None) and form.is_instructor.data
            )

            user = User(
                username=form.username.data,
                email=form.email.data,
                password=hashed_password,
                full_name=form.username.data,
                is_instructor=False,                     # always False at signup
                instructor_request=requested_instructor # admin approve karega
            )

            db.session.add(user)
            db.session.commit()

            activity = UserActivity(
                user_id=user.id,
                activity_type='register',
                description=f'New user registered: {user.username}'
            )
            db.session.add(activity)
            db.session.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.exception("Registration failed")
            flash(f'Registration failed: {str(e)}', 'danger')

    return render_template('register.html', form=form)

@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserForm()

    if form.validate_on_submit():
        try:
            # ... checks ...

            user.username = form.username.data
            user.email = form.email.data
            user.full_name = form.full_name.data
            user.is_instructor = form.is_instructor.data
            user.is_admin = form.is_admin.data

            # Password optional — sirf tab update karo jab diya ho
            if form.password.data:                      # <-- ye check hona chahiye
                user.password = generate_password_hash(form.password.data)

            db.session.commit()
            flash(f'User {user.username} updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            logger.exception("Admin edit user failed")
            flash(f'Error updating user: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.full_name.data = user.full_name
        form.is_instructor.data = user.is_instructor
        form.is_admin.data = user.is_admin

    return render_template('admin/edit_user.html', form=form, user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)

            activity = UserActivity(
                user_id=user.id,
                activity_type='login',
                description='User logged in'
            )
            db.session.add(activity)
            db.session.commit()

            flash(f'Welcome back, {user.username}!', 'success')

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    if current_user.is_authenticated:
        activity = UserActivity(
            user_id=current_user.id,
            activity_type='logout',
            description='User logged out'
        )
        db.session.add(activity)
        db.session.commit()

    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ==================== DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_instructor:
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
        total_students = 0
        total_earnings = 0

        for course in courses:
            enrollments_count = course.enrollments.count()
            total_students += enrollments_count
            total_earnings += course.price * enrollments_count

        recent_activities = UserActivity.query.filter_by(user_id=current_user.id) \
            .order_by(UserActivity.timestamp.desc()).limit(10).all()

        return render_template(
            'dashboard.html',
            courses=courses,
            instructor=True,
            total_students=total_students,
            total_earnings=total_earnings,
            recent_activities=recent_activities
        )
    else:
        enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
        completed_courses = 0
        total_progress = 0

        for enrollment in enrollments:
            course = enrollment.course
            progress = course.get_progress_for_user(current_user.id)
            total_progress += progress
            if progress == 100:
                completed_courses += 1

        avg_progress = total_progress / len(enrollments) if enrollments else 0
        wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()

        recent_activities = UserActivity.query.filter_by(user_id=current_user.id) \
            .order_by(UserActivity.timestamp.desc()).limit(10).all()

        return render_template(
            'dashboard.html',
            enrollments=enrollments,
            instructor=False,
            completed_courses=completed_courses,
            avg_progress=avg_progress,
            wishlist_count=wishlist_count,
            recent_activities=recent_activities
        )


# ==================== COURSE ROUTES ====================

@app.route('/courses', methods=['GET', 'POST'])
def courses():
    form = CourseFilterForm()
    query = Course.query

    if request.method == 'POST' and form.validate_on_submit():
        category = form.category.data
        level = form.level.data
        price_range = form.price_range.data
        sort_by = form.sort_by.data
    else:
        category = request.args.get('category', 'all')
        level = request.args.get('level', 'all')
        price_range = request.args.get('price_range', 'all')
        sort_by = request.args.get('sort', 'newest')

    if category and category != 'all':
        query = query.filter(Course.category == category)

    if level and level != 'all':
        query = query.filter(Course.level == level)

    if price_range and price_range != 'all':
        if price_range == 'free':
            query = query.filter(Course.price == 0)
        elif price_range == 'paid':
            query = query.filter(Course.price > 0)
        elif price_range == 'under_50':
            query = query.filter(Course.price < 50)
        elif price_range == '50_100':
            query = query.filter(Course.price >= 50, Course.price <= 100)
        elif price_range == 'over_100':
            query = query.filter(Course.price > 100)

    search = request.args.get('search', '')
    if search:
        query = query.filter(
            db.or_(
                Course.title.contains(search),
                Course.description.contains(search)
            )
        )

    all_courses = query.all()

    if sort_by == 'popular':
        all_courses.sort(key=lambda c: c.enrollments.count(), reverse=True)
    elif sort_by == 'rating':
        all_courses.sort(key=lambda c: c.avg_rating or 0, reverse=True)
    elif sort_by == 'price_low':
        all_courses.sort(key=lambda c: c.price)
    elif sort_by == 'price_high':
        all_courses.sort(key=lambda c: c.price, reverse=True)
    else:
        all_courses.sort(key=lambda c: c.created_at, reverse=True)

    all_prices = [c.price for c in Course.query.all()]
    max_price_filter = max(all_prices) if all_prices else 1000

    return render_template(
        'courses.html',
        courses=all_courses,
        form=form,
        search_term=search,
        sort_by=sort_by,
        max_price_filter=max_price_filter
    )


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    is_in_wishlist = False

    if current_user.is_authenticated:
        is_enrolled = Enrollment.query.filter_by(
            user_id=current_user.id, course_id=course_id
        ).first() is not None

        is_in_wishlist = Wishlist.query.filter_by(
            user_id=current_user.id, course_id=course_id
        ).first() is not None

    reviews = Review.query.filter_by(course_id=course_id) \
        .order_by(Review.created_at.desc()).all()

    related_courses = Course.query.filter(
        Course.instructor_id == course.instructor_id,
        Course.id != course_id
    ).limit(3).all()

    user_progress = 0
    if is_enrolled and current_user.is_authenticated:
        user_progress = course.get_progress_for_user(current_user.id)

    return render_template(
        'course_detail.html',
        course=course,
        is_enrolled=is_enrolled,
        is_in_wishlist=is_in_wishlist,
        reviews=reviews,
        related_courses=related_courses,
        user_progress=user_progress
    )


@app.route('/enroll/<int:course_id>')
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)

    existing = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()

    if existing:
        flash('You are already enrolled in this course!', 'warning')
    else:
        try:
            enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
            db.session.add(enrollment)

            activity = UserActivity(
                user_id=current_user.id,
                activity_type='enroll',
                description=f'Enrolled in course: {course.title}'
            )
            db.session.add(activity)
            db.session.commit()

            flash(f'Successfully enrolled in {course.title}!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.exception("Enroll failed")
            flash(f'Error enrolling in course: {str(e)}', 'danger')

    return redirect(url_for('course_detail', course_id=course_id))


@app.route('/course/<int:course_id>/learn')
@login_required
def learn_course(course_id):
    course = Course.query.get_or_404(course_id)
    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()

    if not enrollment and course.instructor_id != current_user.id:
        flash('Please enroll in this course first.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.order).all()
    total_lessons = len(lessons)
    completed_lessons = LessonProgress.query.filter_by(
        user_id=current_user.id, completed=True
    ).join(Lesson).filter(Lesson.course_id == course_id).count()

    progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    current_lesson_id = request.args.get('lesson_id', type=int)
    current_lesson = None
    if current_lesson_id:
        current_lesson = Lesson.query.get_or_404(current_lesson_id)
        if current_lesson.course_id != course_id:
            current_lesson = None

    return render_template(
        'learn_course.html',
        course=course,
        lessons=lessons,
        progress_percentage=progress_percentage,
        completed_lessons=completed_lessons,
        current_lesson=current_lesson
    )


# ==================== INSTRUCTOR ROUTES ====================

@app.route('/instructor/add_course', methods=['GET', 'POST'])
@login_required
def add_course():
    if not current_user.is_instructor:
        flash('Only instructors can add courses.', 'danger')
        return redirect(url_for('dashboard'))

    form = CourseForm()

    if form.validate_on_submit():
        try:
            # ============ PRICE FIX ============
            # Agar price None/empty/0 hai toh 0.0 set karo
            price_value = form.price.data
            if price_value is None or price_value == '':
                price_value = 0.0
            else:
                try:
                    price_value = float(price_value)
                except (ValueError, TypeError):
                    price_value = 0.0
            # ===================================

            image_filename = None
            if form.image.data and allowed_file(form.image.data.filename):
                filename = secure_filename(form.image.data.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                form.image.data.save(filepath)
                image_filename = unique_filename

            course = Course(
                title=form.title.data,
                description=form.description.data,
                price=price_value,              # <-- ye use karo
                image_url=form.image_url.data if form.image_url.data else (
                    f'/static/uploads/{image_filename}' if image_filename else None
                ),
                instructor_id=current_user.id,
                category=form.category.data,
                level=form.level.data
            )
            db.session.add(course)
            db.session.commit()

            activity = UserActivity(
                user_id=current_user.id,
                activity_type='create_course',
                description=f'Created new course: {course.title}'
            )
            db.session.add(activity)
            db.session.commit()

            flash('Course created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.exception("Course creation failed")
            flash(f'Error creating course: {str(e)}', 'danger')

    return render_template('add_course.html', form=form)

@app.route('/instructor/course/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('dashboard'))

    form = CourseForm()

    if form.validate_on_submit():
        try:
            course.title = form.title.data
            course.description = form.description.data
            course.price = form.price.data
            course.category = form.category.data
            course.level = form.level.data

            if form.image_url.data:
                course.image_url = form.image_url.data
            elif form.image.data and allowed_file(form.image.data.filename):
                filename = secure_filename(form.image.data.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                form.image.data.save(filepath)
                course.image_url = f'/static/uploads/{unique_filename}'

            db.session.commit()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('course_detail', course_id=course.id))
        except Exception as e:
            db.session.rollback()
            logger.exception("Course update failed")
            flash(f'Error updating course: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.title.data = course.title
        form.description.data = course.description
        form.price.data = course.price
        form.image_url.data = course.image_url or ''
        form.category.data = getattr(course, 'category', 'other')
        form.level.data = getattr(course, 'level', 'beginner')

    return render_template('edit_course.html', form=form, course=course)

@app.route('/instructor/course/<int:course_id>/edit-image', methods=['GET', 'POST'])
@login_required
def edit_course_image(course_id):
    """Edit course image (instructor only)."""
    course = Course.query.get_or_404(course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this course image.', 'danger')
        return redirect(url_for('dashboard'))

    suggested_images = [
        {'url': 'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=800&h=400&fit=crop', 'name': 'Programming'},
        {'url': 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=800&h=400&fit=crop', 'name': 'Web Development'},
        {'url': 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&h=400&fit=crop', 'name': 'Business'},
        {'url': 'https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800&h=400&fit=crop', 'name': 'Design'},
        {'url': 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&h=400&fit=crop', 'name': 'Data Science'},
        {'url': 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800&h=400&fit=crop', 'name': 'Coding'},
    ]

    if request.method == 'POST':
        try:
            image_url = request.form.get('image_url', '').strip()
            image_file = request.files.get('image')

            # Priority 1: File upload
            if image_file and image_file.filename and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(filepath)
                course.image_url = f'/static/uploads/{unique_filename}'

            # Priority 2: URL
            elif image_url:
                course.image_url = image_url

            else:
                flash('Please upload an image or paste a URL.', 'warning')
                return redirect(url_for('edit_course_image', course_id=course_id))

            db.session.commit()

            activity = UserActivity(
                user_id=current_user.id,
                activity_type='edit_course',
                description=f'Updated image for course: {course.title}'
            )
            db.session.add(activity)
            db.session.commit()

            flash('Course image updated successfully!', 'success')
            return redirect(url_for('edit_course', course_id=course.id))

        except Exception as e:
            db.session.rollback()
            logger.exception("Course image update failed")
            flash(f'Error updating course image: {str(e)}', 'danger')

    return render_template(
        'edit_course_image.html',
        course=course,
        suggested_images=suggested_images
    )

@app.route('/instructor/course/<int:course_id>/add_lesson', methods=['GET', 'POST'])
@login_required
def add_lesson(course_id):
    course = Course.query.get_or_404(course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to add lessons to this course.', 'danger')
        return redirect(url_for('dashboard'))

    form = LessonForm()
    if form.validate_on_submit():
        try:
            lesson = Lesson(
                title=form.title.data,
                content=form.content.data,
                video_url=form.video_url.data,
                order=form.order.data,
                course_id=course_id
            )
            db.session.add(lesson)
            db.session.commit()

            activity = UserActivity(
                user_id=current_user.id,
                activity_type='add_lesson',
                description=f'Added lesson "{lesson.title}" to course: {course.title}'
            )
            db.session.add(activity)
            db.session.commit()

            flash('Lesson added successfully!', 'success')
            return redirect(url_for('learn_course', course_id=course_id))
        except Exception as e:
            db.session.rollback()
            logger.exception("Lesson add failed")
            flash(f'Error adding lesson: {str(e)}', 'danger')

    return render_template('add_lesson.html', form=form, course=course)


@app.route('/instructor/course/<int:course_id>/manage-lessons')
@login_required
def manage_lessons(course_id):
    course = Course.query.get_or_404(course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to manage this course.', 'danger')
        return redirect(url_for('dashboard'))

    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.order).all()

    lessons_with_video = sum(1 for lesson in lessons if lesson.video_url)
    lessons_with_quizzes = sum(1 for lesson in lessons if lesson.quizzes.count() > 0)

    return render_template(
        'manage_lessons.html',
        course=course,
        lessons=lessons,
        lessons_with_video=lessons_with_video,
        lessons_with_quizzes=lessons_with_quizzes
    )


@app.route('/instructor/lesson/<int:lesson_id>/delete')
@login_required
def delete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course_id = lesson.course_id
    course = Course.query.get(course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to delete this lesson.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        lesson_title = lesson.title
        LessonProgress.query.filter_by(lesson_id=lesson_id).delete()
        db.session.delete(lesson)
        db.session.commit()

        activity = UserActivity(
            user_id=current_user.id,
            activity_type='delete_lesson',
            description=f'Deleted lesson "{lesson_title}" from course: {course.title}'
        )
        db.session.add(activity)
        db.session.commit()

        flash(f'Lesson "{lesson_title}" has been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception("Lesson delete failed")
        flash(f'Error deleting lesson: {str(e)}', 'danger')

    return redirect(url_for('manage_lessons', course_id=course_id))


@app.route('/instructor/course/<int:course_id>/delete')
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to delete this course.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        course_title = course.title

        for lesson in course.lessons.all():
            LessonProgress.query.filter_by(lesson_id=lesson.id).delete()
            Quiz.query.filter_by(lesson_id=lesson.id).delete()

        Lesson.query.filter_by(course_id=course_id).delete()
        Enrollment.query.filter_by(course_id=course_id).delete()
        Review.query.filter_by(course_id=course_id).delete()
        Wishlist.query.filter_by(course_id=course_id).delete()

        db.session.delete(course)
        db.session.commit()

        flash(f'Course "{course_title}" and all associated data have been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception("Course delete failed")
        flash(f'Error deleting course: {str(e)}', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/instructor/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get(lesson.course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this lesson.', 'danger')
        return redirect(url_for('dashboard'))

    form = LessonForm()

    if form.validate_on_submit():
        try:
            lesson.title = form.title.data
            lesson.content = form.content.data
            lesson.video_url = form.video_url.data
            lesson.order = form.order.data
            db.session.commit()

            activity = UserActivity(
                user_id=current_user.id,
                activity_type='edit_lesson',
                description=f'Edited lesson "{lesson.title}"'
            )
            db.session.add(activity)
            db.session.commit()

            flash('Lesson updated successfully!', 'success')
            return redirect(url_for('manage_lessons', course_id=course.id))
        except Exception as e:
            db.session.rollback()
            logger.exception("Lesson edit failed")
            flash(f'Error updating lesson: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.title.data = lesson.title
        form.content.data = lesson.content
        form.video_url.data = lesson.video_url
        form.order.data = lesson.order

    return render_template('edit_lesson.html', form=form, lesson=lesson, course=course)


# ==================== PROFILE ROUTES ====================

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user, QuizAttempt=QuizAttempt)


@app.route('/profile/<username>')
def public_profile(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user.is_instructor:
        total_courses = user.created_courses.count()
        courses = user.created_courses.limit(6).all()
    else:
        total_courses = user.enrolled_courses.count()
        courses = [e.course for e in user.enrolled_courses.limit(6).all()]

    completed_lessons = LessonProgress.query.filter_by(user_id=user.id, completed=True).count()
    recent_activities = UserActivity.query.filter_by(user_id=user.id) \
        .order_by(UserActivity.timestamp.desc()).limit(10).all()

    is_owner = current_user.is_authenticated and current_user.id == user.id

    return render_template(
        'public_profile.html',
        user=user,
        total_courses=total_courses,
        completed_lessons=completed_lessons,
        recent_activities=recent_activities,
        is_owner=is_owner,
        courses=courses
    )


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm()

    if form.validate_on_submit():
        try:
            current_user.full_name = form.full_name.data
            current_user.bio = form.bio.data
            current_user.location = form.location.data
            current_user.website = form.website.data
            current_user.occupation = form.occupation.data
            current_user.education = form.education.data
            current_user.skills = form.skills.data
            current_user.social_twitter = form.social_twitter.data
            current_user.social_linkedin = form.social_linkedin.data
            current_user.social_github = form.social_github.data
            db.session.commit()

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            logger.exception("Profile update failed")
            flash(f'Error updating profile: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.full_name.data = current_user.full_name
        form.bio.data = current_user.bio
        form.location.data = current_user.location
        form.website.data = current_user.website
        form.occupation.data = current_user.occupation
        form.education.data = current_user.education
        form.skills.data = current_user.skills
        form.social_twitter.data = current_user.social_twitter
        form.social_linkedin.data = current_user.social_linkedin
        form.social_github.data = current_user.social_github

    return render_template('edit_profile.html', form=form)


@app.route('/profile/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    form = AvatarForm()

    if form.validate_on_submit():
        try:
            if form.avatar.data:
                filename = secure_filename(
                    f"avatar_{current_user.id}_{uuid.uuid4().hex}_{form.avatar.data.filename}"
                )
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                form.avatar.data.save(filepath)

                if current_user.avatar and '/static/uploads/' in current_user.avatar:
                    old_file = current_user.avatar.replace('/static/uploads/', '')
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_file)
                    if os.path.exists(old_path):
                        os.remove(old_path)

                current_user.avatar = f'/static/uploads/{filename}'
                db.session.commit()
                flash('Profile picture updated!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.exception("Avatar upload failed")
            flash(f'Error uploading avatar: {str(e)}', 'danger')

    return redirect(url_for('profile'))


@app.route('/profile/remove-avatar')
@login_required
def remove_avatar():
    try:
        if current_user.avatar and '/static/uploads/' in current_user.avatar:
            old_file = current_user.avatar.replace('/static/uploads/', '')
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_file)
            if os.path.exists(old_path):
                os.remove(old_path)

        current_user.avatar = None
        db.session.commit()
        flash('Profile picture removed.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception("Avatar removal failed")
        flash(f'Error removing avatar: {str(e)}', 'danger')

    return redirect(url_for('profile'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm()

    if form.validate_on_submit():
        if not check_password_hash(current_user.password, form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html', form=form)

        current_user.password = generate_password_hash(form.new_password.data)
        db.session.commit()

        flash('Your password has been changed successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('change_password.html', form=form)


# ==================== LESSON PROGRESS ====================

@app.route('/lesson/<int:lesson_id>/complete')
@login_required
def complete_lesson(lesson_id):
    """Mark lesson as complete (one-way — no toggle)."""
    lesson = Lesson.query.get_or_404(lesson_id)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=lesson.course_id
    ).first()
    if not enrollment:
        flash('You must be enrolled in this course to mark lessons as complete.', 'danger')
        return redirect(url_for('course_detail', course_id=lesson.course_id))

    try:
        progress = LessonProgress.query.filter_by(
            user_id=current_user.id, lesson_id=lesson_id
        ).first()

        if not progress:
            progress = LessonProgress(user_id=current_user.id, lesson_id=lesson_id)
            db.session.add(progress)

        progress.completed = True
        progress.completed_at = progress.completed_at or datetime.utcnow()
        progress.last_watched = datetime.utcnow()

        activity = UserActivity(
            user_id=current_user.id,
            activity_type='complete_lesson',
            description=f'Completed lesson: {lesson.title}'
        )
        db.session.add(activity)
        db.session.commit()

        flash('Lesson marked as completed!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception("Lesson complete failed")
        flash(f'Error updating lesson progress: {str(e)}', 'danger')

    return redirect(url_for('learn_course', course_id=lesson.course_id))


# ==================== REVIEWS ====================

@app.route('/course/<int:course_id>/review', methods=['GET', 'POST'])
@login_required
def add_review(course_id):
    course = Course.query.get_or_404(course_id)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()
    if not enrollment:
        flash('You must be enrolled in this course to leave a review.', 'danger')
        return redirect(url_for('course_detail', course_id=course_id))

    existing_review = Review.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()
    if existing_review:
        flash('You have already reviewed this course.', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    form = ReviewForm()
    if form.validate_on_submit():
        try:
            review = Review(
                rating=form.rating.data,
                comment=form.comment.data,
                user_id=current_user.id,
                course_id=course_id
            )
            db.session.add(review)
            db.session.commit()

            course.update_rating()

            flash('Thank you for your review!', 'success')
            return redirect(url_for('course_detail', course_id=course_id))
        except Exception as e:
            db.session.rollback()
            logger.exception("Review add failed")
            flash(f'Error submitting review: {str(e)}', 'danger')

    return render_template('add_review.html', form=form, course=course)


# ==================== WISHLIST ====================

@app.route('/wishlist/add/<int:course_id>')
@login_required
def add_to_wishlist(course_id):
    course = Course.query.get_or_404(course_id)

    existing = Wishlist.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()
    if existing:
        flash('Course already in your wishlist!', 'info')
    else:
        try:
            wishlist_item = Wishlist(user_id=current_user.id, course_id=course_id)
            db.session.add(wishlist_item)
            db.session.commit()
            flash(f'Added {course.title} to your wishlist!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.exception("Wishlist add failed")
            flash(f'Error adding to wishlist: {str(e)}', 'danger')

    return redirect(url_for('course_detail', course_id=course_id))


@app.route('/wishlist/remove/<int:course_id>')
@login_required
def remove_from_wishlist(course_id):
    wishlist_item = Wishlist.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()
    if wishlist_item:
        try:
            db.session.delete(wishlist_item)
            db.session.commit()
            flash('Removed from wishlist', 'success')
        except Exception as e:
            db.session.rollback()
            logger.exception("Wishlist remove failed")
            flash(f'Error removing from wishlist: {str(e)}', 'danger')

    return redirect(url_for('wishlist'))


@app.route('/wishlist')
@login_required
def wishlist():
    wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
    wishlist_course_ids = [item.course_id for item in wishlist_items]

    all_courses = Course.query.all()
    if wishlist_course_ids:
        suggested_courses = [c for c in all_courses if c.id not in wishlist_course_ids]
        suggested_courses.sort(key=lambda c: c.enrollments.count(), reverse=True)
    else:
        suggested_courses = sorted(all_courses, key=lambda c: c.enrollments.count(), reverse=True)

    suggested_courses = suggested_courses[:3]

    return render_template(
        'wishlist.html',
        wishlist_items=wishlist_items,
        suggested_courses=suggested_courses
    )


# ==================== QUIZ ROUTES ====================

@app.route('/instructor/lesson/<int:lesson_id>/add-quiz', methods=['GET', 'POST'])
@login_required
def add_quiz(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get(lesson.course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to add quiz to this lesson.', 'danger')
        return redirect(url_for('dashboard'))

    form = QuizForm()
    if form.validate_on_submit():
        try:
            quiz = Quiz(
                lesson_id=lesson_id,
                question=form.question.data,
                option_a=form.option_a.data,
                option_b=form.option_b.data,
                option_c=form.option_c.data,
                option_d=form.option_d.data,
                correct_answer=form.correct_answer.data,
                points=form.points.data
            )
            db.session.add(quiz)
            db.session.commit()
            flash('Quiz question added successfully!', 'success')
            return redirect(url_for('manage_quizzes', lesson_id=lesson_id))
        except Exception as e:
            db.session.rollback()
            logger.exception("Quiz add failed")
            flash(f'Error adding quiz: {str(e)}', 'danger')

    quizzes = Quiz.query.filter_by(lesson_id=lesson_id).all()
    return render_template('add_quiz.html', form=form, lesson=lesson, quizzes=quizzes)


@app.route('/instructor/quiz/<int:quiz_id>/delete')
@login_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    lesson_id = quiz.lesson_id
    lesson = Lesson.query.get(lesson_id)
    course = Course.query.get(lesson.course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to delete this quiz.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        QuizAttempt.query.filter_by(quiz_id=quiz_id).delete()
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz question deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception("Quiz delete failed")
        flash(f'Error deleting quiz: {str(e)}', 'danger')

    return redirect(url_for('manage_quizzes', lesson_id=lesson_id))


@app.route('/lesson/<int:lesson_id>/quiz', methods=['GET', 'POST'])
@login_required
def take_quiz(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get(lesson.course_id)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course.id
    ).first()
    if not enrollment:
        flash('You must be enrolled in this course to take the quiz.', 'danger')
        return redirect(url_for('course_detail', course_id=course.id))

    quizzes = Quiz.query.filter_by(lesson_id=lesson_id).all()

    if not quizzes:
        flash('No quiz available for this lesson yet.', 'info')
        return redirect(url_for('learn_course', course_id=course.id))

    if request.method == 'POST':
        try:
            score = 0
            total = len(quizzes)

            for quiz in quizzes:
                user_answer = request.form.get(f'quiz_{quiz.id}')
                if user_answer and quiz.check_answer(user_answer):
                    score += 1

            percentage = (score / total) * 100
            passed = percentage >= 70

            # Save one attempt per question (matches existing schema)
            for quiz in quizzes:
                user_answer = request.form.get(f'quiz_{quiz.id}')
                is_correct = user_answer and quiz.check_answer(user_answer)

                attempt = QuizAttempt(
                    user_id=current_user.id,
                    quiz_id=quiz.id,
                    score=1 if is_correct else 0,
                    total_questions=1,
                    percentage=100 if is_correct else 0,
                    passed=is_correct
                )
                db.session.add(attempt)

            if passed:
                progress = LessonProgress.query.filter_by(
                    user_id=current_user.id, lesson_id=lesson_id
                ).first()
                if not progress:
                    progress = LessonProgress(user_id=current_user.id, lesson_id=lesson_id)
                    db.session.add(progress)
                progress.completed = True
                progress.completed_at = datetime.utcnow()

                flash(
                    f'🎉 Congratulations! You scored {score}/{total} '
                    f'({percentage:.0f}%) and passed the quiz!',
                    'success'
                )
            else:
                flash(
                    f'📚 You scored {score}/{total} ({percentage:.0f}%). '
                    f'You need 70% to pass. Please review and try again.',
                    'warning'
                )

            db.session.commit()
            return redirect(url_for('learn_course', course_id=course.id))
        except Exception as e:
            db.session.rollback()
            logger.exception("Quiz submit failed")
            flash(f'Error submitting quiz: {str(e)}', 'danger')

    return render_template('take_quiz.html', lesson=lesson, quizzes=quizzes)


@app.route('/quiz/results')
@login_required
def quiz_results():
    attempts = QuizAttempt.query.filter_by(user_id=current_user.id) \
        .order_by(QuizAttempt.attempted_at.desc()).all()
    return render_template('quiz_results.html', attempts=attempts)


@app.route('/instructor/lesson/<int:lesson_id>/manage-quizzes')
@login_required
def manage_quizzes(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = Course.query.get(lesson.course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to manage quizzes for this lesson.', 'danger')
        return redirect(url_for('dashboard'))

    quizzes = Quiz.query.filter_by(lesson_id=lesson_id).all()
    return render_template('manage_quizzes.html', lesson=lesson, quizzes=quizzes)


@app.route('/instructor/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    lesson = Lesson.query.get(quiz.lesson_id)
    course = Course.query.get(lesson.course_id)

    if course.instructor_id != current_user.id:
        flash('You do not have permission to edit this quiz.', 'danger')
        return redirect(url_for('dashboard'))

    form = QuizForm()

    if form.validate_on_submit():
        try:
            quiz.question = form.question.data
            quiz.option_a = form.option_a.data
            quiz.option_b = form.option_b.data
            quiz.option_c = form.option_c.data
            quiz.option_d = form.option_d.data
            quiz.correct_answer = form.correct_answer.data
            quiz.points = form.points.data
            db.session.commit()

            flash('Quiz question updated successfully!', 'success')
            return redirect(url_for('manage_quizzes', lesson_id=quiz.lesson_id))
        except Exception as e:
            db.session.rollback()
            logger.exception("Quiz edit failed")
            flash(f'Error updating quiz: {str(e)}', 'danger')

    elif request.method == 'GET':
        form.question.data = quiz.question
        form.option_a.data = quiz.option_a
        form.option_b.data = quiz.option_b
        form.option_c.data = quiz.option_c
        form.option_d.data = quiz.option_d
        form.correct_answer.data = quiz.correct_answer
        form.points.data = quiz.points

    return render_template('edit_quiz.html', form=form, quiz=quiz, lesson=lesson)


# ==================== API ROUTES ====================

@app.route('/api/course/<int:course_id>/progress')
@login_required
def get_course_progress(course_id):
    course = Course.query.get_or_404(course_id)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()
    if not enrollment and course.instructor_id != current_user.id:
        return jsonify({'error': 'Not enrolled'}), 403

    total_lessons = course.lessons.count()
    completed_lessons = LessonProgress.query.filter_by(
        user_id=current_user.id, completed=True
    ).join(Lesson).filter(Lesson.course_id == course_id).count()

    progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

    return jsonify({
        'course_id': course_id,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'progress': round(progress, 1)
    })


@app.route('/api/check-email', methods=['POST'])
def check_email():
    data = request.get_json() or {}
    email = data.get('email', '')
    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': user is not None})


@app.route('/api/check-username', methods=['POST'])
def check_username():
    data = request.get_json() or {}
    username = data.get('username', '')
    user = User.query.filter_by(username=username).first()
    return jsonify({'exists': user is not None})


# ==================== ADMIN ROUTES ====================

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    form = AdminUserForm()
    users = User.query.all()
    return render_template('admin/users.html', users=users, form=form)


@app.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_user():
    form = AdminUserForm()

    if form.validate_on_submit():
        try:
            if not form.password.data:
                flash('Password is required for new users.', 'danger')
                return render_template('admin/add_user.html', form=form)

            if User.query.filter_by(email=form.email.data).first():
                flash('Email already exists.', 'danger')
                return render_template('admin/add_user.html', form=form)

            if User.query.filter_by(username=form.username.data).first():
                flash('Username already exists.', 'danger')
                return render_template('admin/add_user.html', form=form)

            user = User(
                username=form.username.data,
                email=form.email.data,
                password=generate_password_hash(form.password.data),
                full_name=form.full_name.data or form.username.data,
                is_instructor=form.is_instructor.data,
                is_admin=form.is_admin.data
            )
            db.session.add(user)
            db.session.commit()

            flash(f'User {user.username} created successfully!', 'success')
            return redirect(url_for('admin_users'))
        except Exception as e:
            db.session.rollback()
            logger.exception("Admin add user failed")
            flash(f'Error creating user: {str(e)}', 'danger')

    return render_template('admin/add_user.html', form=form)

@app.route('/admin/user/<int:user_id>/delete')
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'User {username} has been deleted.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/courses')
@login_required
@admin_required
def admin_courses():
    courses = Course.query.all()
    return render_template('admin/courses.html', courses=courses)


# ==================== STATIC FILES ====================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ==================== OTHER ROUTES ====================

@app.route('/leaderboard')
def leaderboard():
    """Leaderboard showing top students"""
    from sqlalchemy import func

    # Top users by average quiz score
    top_users = db.session.query(
        User,
        func.avg(QuizAttempt.percentage).label('avg_score'),
        func.count(QuizAttempt.id).label('total_attempts'),
        func.sum(QuizAttempt.score).label('total_score')
    ).join(QuizAttempt, User.id == QuizAttempt.user_id) \
     .group_by(User.id) \
     .order_by(func.avg(QuizAttempt.percentage).desc()) \
     .limit(10).all()

    # Top courses by enrollment count — Python-side sort (simpler & safe)
    all_courses = Course.query.all()
    top_courses = sorted(
        all_courses,
        key=lambda c: c.enrollments.count(),
        reverse=True
    )[:5]

    return render_template('leaderboard.html', top_users=top_users, top_courses=top_courses)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('courses'))

    courses = Course.query.filter(
        db.or_(
            Course.title.contains(query),
            Course.description.contains(query)
        )
    ).all()

    users = User.query.filter(
        db.or_(
            User.username.contains(query),
            User.full_name.contains(query)
        )
    ).limit(5).all()

    return render_template('search_results.html', query=query, courses=courses, users=users)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('index'))
    return render_template('contact.html', form=form)


@app.route('/newsletter', methods=['POST'])
def newsletter():
    form = NewsletterForm()
    if form.validate_on_submit():
        flash('Successfully subscribed to newsletter!', 'success')
    else:
        flash('Invalid email address.', 'danger')
    return redirect(url_for('index'))


# ==================== CERTIFICATE ====================

@app.route('/certificate/<int:course_id>')
@login_required
def generate_certificate(course_id):
    """Generate professional course completion certificate."""
    course = Course.query.get_or_404(course_id)

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()
    if not enrollment:
        flash('You must be enrolled in this course to get a certificate.', 'danger')
        return redirect(url_for('course_detail', course_id=course_id))

    lessons = Lesson.query.filter_by(course_id=course_id).all()
    completed_count = 0
    for lesson in lessons:
        if LessonProgress.query.filter_by(
            user_id=current_user.id, lesson_id=lesson.id, completed=True
        ).first():
            completed_count += 1

    if completed_count < len(lessons):
        flash(
            f'Please complete all lessons to get your certificate! '
            f'({completed_count}/{len(lessons)} completed)',
            'warning'
        )
        return redirect(url_for('learn_course', course_id=course_id))

    try:
        buffer = io.BytesIO()
        width, height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        # Background
        c.setFillColor(colors.Color(0.98, 0.97, 0.92))
        c.rect(0, 0, width, height, fill=1, stroke=0)

        # Outer border
        c.setStrokeColor(colors.Color(0.78, 0.66, 0.30))
        c.setLineWidth(6)
        c.rect(40, 40, width - 80, height - 80, fill=0, stroke=1)

        # Inner border
        c.setLineWidth(2)
        c.rect(55, 55, width - 110, height - 110, fill=0, stroke=1)

        # Corner decorations
        def draw_corner(x, y, size_x=30, size_y=30):
            c.setStrokeColor(colors.Color(0.78, 0.66, 0.30))
            c.setLineWidth(3)
            c.line(x, y, x + size_x, y)
            c.line(x, y, x, y + size_y)

        draw_corner(55, 55)
        draw_corner(width - 55, 55, -30)
        draw_corner(55, height - 55, 30, -30)
        draw_corner(width - 55, height - 55, -30, -30)

        # Title
        c.setFillColor(colors.Color(0.78, 0.66, 0.30))
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(width / 2, height - 120, "CERTIFICATE OF COMPLETION")

        # Decorative line
        c.setStrokeColor(colors.Color(0.78, 0.66, 0.30))
        c.setLineWidth(1.5)
        line_width = 160
        c.line(width / 2 - line_width, height - 138, width / 2 + line_width, height - 138)

        # Subtitle
        c.setFillColor(colors.Color(0.4, 0.4, 0.4))
        c.setFont("Helvetica", 13)
        c.drawCentredString(width / 2, height - 165, "This certificate is proudly presented to")

        # Student name
        c.setFillColor(colors.Color(0.15, 0.15, 0.15))
        c.setFont("Helvetica-Bold", 40)
        student_name = current_user.full_name or current_user.username
        c.drawCentredString(width / 2, height - 230, student_name)

        # Line under name
        c.setStrokeColor(colors.Color(0.78, 0.66, 0.30))
        c.setLineWidth(2)
        name_line_width = 220
        c.line(width / 2 - name_line_width, height - 248,
               width / 2 + name_line_width, height - 248)

        # Completion text
        c.setFillColor(colors.Color(0.3, 0.3, 0.3))
        c.setFont("Helvetica", 15)
        c.drawCentredString(width / 2, height - 290, "for successfully completing the course")

        # Course title
        c.setFillColor(colors.Color(0.2, 0.4, 0.6))
        c.setFont("Helvetica-Bold", 26)
        course_title = (course.title[:50] + "...") if len(course.title) > 50 else course.title
        c.drawCentredString(width / 2, height - 340, course_title)

        # Badge
        badge_y = height - 390
        c.setFillColor(colors.Color(0.78, 0.66, 0.30))
        c.roundRect(width / 2 - 90, badge_y, 180, 32, 16, fill=1, stroke=0)
        c.setFillColor(colors.Color(1, 1, 1))
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, badge_y + 12, "100% COMPLETE")

        # Extra text
        c.setFillColor(colors.Color(0.4, 0.4, 0.4))
        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2, height - 440,
                            "This certificate acknowledges outstanding performance and dedication")
        c.drawCentredString(width / 2, height - 458,
                            "in mastering all learning objectives and course requirements.")

        # Signatures
        y_signature = 120
        sig_width = 170

        c.setStrokeColor(colors.Color(0.2, 0.2, 0.2))
        c.setLineWidth(1.5)
        sig_x = width / 2 - 200
        c.line(sig_x, y_signature + 10, sig_x + sig_width, y_signature + 10)
        c.setFillColor(colors.Color(0.2, 0.2, 0.2))
        c.setFont("Helvetica", 11)
        c.drawCentredString(sig_x + sig_width / 2, y_signature - 8, "Course Instructor")

        sig_x2 = width / 2 + 30
        c.line(sig_x2, y_signature + 10, sig_x2 + sig_width, y_signature + 10)
        c.drawCentredString(sig_x2 + sig_width / 2, y_signature - 8, "Academic Director")

        # Date
        c.setFillColor(colors.Color(0.4, 0.4, 0.4))
        c.setFont("Helvetica", 10)
        date_str = datetime.now().strftime("%B %d, %Y")
        c.drawCentredString(width / 2, y_signature - 50, f"Issued on: {date_str}")

        # Certificate ID
        c.setFillColor(colors.Color(0.6, 0.6, 0.6))
        c.setFont("Helvetica", 8)
        cert_id = f"CERT-{course.id}-{current_user.id}-{datetime.now().strftime('%Y%m%d')}"
        c.drawCentredString(width / 2, 45, f"Certificate ID: {cert_id}")

        c.save()
        buffer.seek(0)

        filename = f"certificate_{course.title.replace(' ', '_')}_{current_user.username}.pdf"
        return make_response(buffer.getvalue(), 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'inline; filename={filename}'
        })

    except Exception as e:
        logger.exception("Certificate generation failed")
        flash(f'Error generating certificate: {str(e)}', 'danger')
        return redirect(url_for('learn_course', course_id=course_id))


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        logger.info("Database tables ensured.")
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='127.0.0.1', port=5000)