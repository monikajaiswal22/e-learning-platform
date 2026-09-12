# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ==================== USER ====================

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)

    # Roles
    is_instructor = db.Column(db.Boolean, default=False, index=True)
    is_admin = db.Column(db.Boolean, default=False, index=True)
    instructor_request = db.Column(db.Boolean, default=False)  # student ne request bheji hai

    date_joined = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Profile fields
    full_name = db.Column(db.String(120), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.String(300), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    occupation = db.Column(db.String(100), nullable=True)
    education = db.Column(db.String(200), nullable=True)
    skills = db.Column(db.Text, nullable=True)
    social_twitter = db.Column(db.String(200), nullable=True)
    social_linkedin = db.Column(db.String(200), nullable=True)
    social_github = db.Column(db.String(200), nullable=True)

    # Relationships
    enrolled_courses = db.relationship(
        'Enrollment', backref='student', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    created_courses = db.relationship(
        'Course', backref='instructor', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    activities = db.relationship(
        'UserActivity', backref='user', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    lesson_progress = db.relationship(
        'LessonProgress', backref='user', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    reviews = db.relationship(
        'Review', backref='user', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    wishlist_items = db.relationship(
        'Wishlist', backref='user', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    quiz_attempts = db.relationship(
        'QuizAttempt', backref='user', lazy='dynamic',
        cascade="all, delete-orphan"
    )

    # ==================== METHODS ====================

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    # ==================== PROPERTIES ====================

    @property
    def role(self):
        """Human-readable role."""
        if self.is_admin:
            return 'admin'
        if self.is_instructor:
            return 'instructor'
        return 'student'

    @property
    def display_name(self):
        return self.full_name or self.username

    @property
    def enrolled_courses_count(self):
        return self.enrolled_courses.count()

    @property
    def created_courses_count(self):
        return self.created_courses.count()

    @property
    def completed_lessons_count(self):
        return self.lesson_progress.filter_by(completed=True).count()

    @property
    def total_quiz_score(self):
        from sqlalchemy import func
        result = db.session.query(func.sum(QuizAttempt.score)).filter(
            QuizAttempt.user_id == self.id
        ).scalar()
        return result or 0

    @property
    def average_quiz_score(self):
        from sqlalchemy import func
        result = db.session.query(func.avg(QuizAttempt.percentage)).filter(
            QuizAttempt.user_id == self.id
        ).scalar()
        return result or 0

    # ==================== HELPERS ====================

    def get_recent_activities(self, limit=10):
        return self.activities.order_by(UserActivity.timestamp.desc()).limit(limit).all()

    def is_enrolled_in(self, course_id):
        return self.enrolled_courses.filter_by(course_id=course_id).first() is not None

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


# ==================== COURSE ====================

class Course(db.Model):
    __tablename__ = 'course'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    instructor_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    price = db.Column(db.Float, default=0.0)
    image_url = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Ratings
    avg_rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)

    # Categorization
    category = db.Column(db.String(50), default='other', index=True)
    level = db.Column(db.String(20), default='beginner', index=True)

    # Relationships
    lessons = db.relationship(
        'Lesson', backref='course', lazy='dynamic',
        cascade="all, delete-orphan", order_by="Lesson.order"
    )
    enrollments = db.relationship(
        'Enrollment', backref='course', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    reviews = db.relationship(
        'Review', backref='course', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    wishlisted_by = db.relationship(
        'Wishlist', backref='course', lazy='dynamic',
        cascade="all, delete-orphan"
    )

    # ==================== PROPERTIES ====================

    @property
    def lessons_count(self):
        return self.lessons.count()

    @property
    def enrollments_count(self):
        return self.enrollments.count()

    @property
    def reviews_count(self):
        return self.reviews.count()

    @property
    def total_earnings(self):
        return self.price * self.enrollments_count

    @property
    def is_free(self):
        return self.price == 0

    # ==================== METHODS ====================

    def get_progress_for_user(self, user_id):
        total_lessons = self.lessons.count()
        if total_lessons == 0:
            return 0

        lesson_ids = [lesson.id for lesson in self.lessons]
        completed_lessons = LessonProgress.query.filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id.in_(lesson_ids),
            LessonProgress.completed == True
        ).count()

        return (completed_lessons / total_lessons) * 100

    def is_user_enrolled(self, user_id):
        return self.enrollments.filter_by(user_id=user_id).first() is not None

    def update_rating(self):
        reviews = self.reviews.all()
        if reviews:
            self.avg_rating = sum(r.rating for r in reviews) / len(reviews)
            self.total_reviews = len(reviews)
        else:
            self.avg_rating = 0.0
            self.total_reviews = 0
        db.session.commit()

    def get_rating_stars(self):
        full_stars = int(self.avg_rating)
        half_star = self.avg_rating - full_stars >= 0.5
        empty_stars = 5 - full_stars - (1 if half_star else 0)

        stars = '★' * full_stars
        if half_star:
            stars += '½'
        stars += '☆' * empty_stars
        return stars

    def __repr__(self):
        return f'<Course {self.title}>'


# ==================== LESSON ====================

class Lesson(db.Model):
    __tablename__ = 'lesson'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(300), nullable=True)
    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_progress = db.relationship(
        'LessonProgress', backref='lesson', lazy='dynamic',
        cascade="all, delete-orphan"
    )
    quizzes = db.relationship(
        'Quiz', backref='lesson', lazy='dynamic',
        cascade="all, delete-orphan"
    )

    # ==================== PROPERTIES ====================

    @property
    def quizzes_count(self):
        return self.quizzes.count()

    @property
    def has_quiz(self):
        return self.quizzes_count > 0

    # ==================== METHODS ====================

    def is_completed_by_user(self, user_id):
        progress = LessonProgress.query.filter_by(
            user_id=user_id,
            lesson_id=self.id,
            completed=True
        ).first()
        return progress is not None

    def get_latest_quiz_attempt(self, user_id):
        """Latest quiz attempt for this lesson (any question)."""
        quiz_ids = [quiz.id for quiz in self.quizzes]
        if not quiz_ids:
            return None
        return QuizAttempt.query.filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id.in_(quiz_ids)
        ).order_by(QuizAttempt.attempted_at.desc()).first()

    def get_all_quiz_attempts(self, user_id):
        quiz_ids = [quiz.id for quiz in self.quizzes]
        return QuizAttempt.query.filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id.in_(quiz_ids)
        ).order_by(QuizAttempt.attempted_at.desc()).all()

    def __repr__(self):
        return f'<Lesson {self.title}>'


# ==================== ENROLLMENT ====================

class Enrollment(db.Model):
    __tablename__ = 'enrollment'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_enrollment'),
    )

    def get_progress_percentage(self):
        course = Course.query.get(self.course_id)
        if course:
            return course.get_progress_for_user(self.user_id)
        return 0

    def mark_completed(self):
        if not self.completed:
            self.completed = True
            self.completed_at = datetime.utcnow()
            db.session.commit()

    def __repr__(self):
        return f'<Enrollment User:{self.user_id} Course:{self.course_id}>'


# ==================== USER ACTIVITY ====================

class UserActivity(db.Model):
    __tablename__ = 'user_activity'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<UserActivity {self.activity_type}>'


# ==================== LESSON PROGRESS ====================

class LessonProgress(db.Model):
    __tablename__ = 'lesson_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    lesson_id = db.Column(
        db.Integer, db.ForeignKey('lesson.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    completed = db.Column(db.Boolean, default=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_watched = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_lesson_progress'),
    )

    def mark_completed(self):
        if not self.completed:
            self.completed = True
            self.completed_at = datetime.utcnow()
            db.session.commit()

    def __repr__(self):
        return f'<LessonProgress User:{self.user_id} Lesson:{self.lesson_id} Completed:{self.completed}>'


# ==================== REVIEW ====================

class Review(db.Model):
    __tablename__ = 'review'

    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_review'),
    )

    def __repr__(self):
        return f'<Review User:{self.user_id} Course:{self.course_id} Rating:{self.rating}>'


# ==================== WISHLIST ====================

class Wishlist(db.Model):
    __tablename__ = 'wishlist'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_wishlist'),
    )

    def __repr__(self):
        return f'<Wishlist User:{self.user_id} Course:{self.course_id}>'


# ==================== QUIZ ====================

class Quiz(db.Model):
    __tablename__ = 'quiz'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(
        db.Integer, db.ForeignKey('lesson.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    question = db.Column(db.String(500), nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)
    points = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attempts = db.relationship(
        'QuizAttempt', backref='quiz', lazy='dynamic',
        cascade="all, delete-orphan"
    )

    # ==================== METHODS ====================

    def check_answer(self, answer):
        return answer and answer.lower() == self.correct_answer.lower()

    def get_attempts_count(self, user_id=None):
        query = self.attempts
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.count()

    def get_average_score(self):
        from sqlalchemy import func
        result = db.session.query(func.avg(QuizAttempt.percentage)).filter(
            QuizAttempt.quiz_id == self.id
        ).scalar()
        return result or 0

    def __repr__(self):
        return f'<Quiz {self.question[:50]}>'


# ==================== QUIZ ATTEMPT ====================

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempt'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    quiz_id = db.Column(
        db.Integer, db.ForeignKey('quiz.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float, default=0.0)
    passed = db.Column(db.Boolean, default=False, index=True)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # ==================== METHODS ====================

    def is_passing(self):
        return self.percentage >= 70

    def get_score_percentage(self):
        if self.total_questions > 0:
            return (self.score / self.total_questions) * 100
        return 0

    def __repr__(self):
        return (
            f'<QuizAttempt User:{self.user_id} '
            f'Quiz:{self.quiz_id} Score:{self.score}/{self.total_questions}>'
        )