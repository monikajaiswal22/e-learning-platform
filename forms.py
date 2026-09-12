# forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    StringField, PasswordField, TextAreaField, FloatField, IntegerField,
    BooleanField, SubmitField, SelectField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Optional, URL, NumberRange, ValidationError
)
import re


# ==================== CUSTOM VALIDATORS ====================

def validate_username(form, field):
    """Custom validator for username (alphanumeric + underscore only)."""
    username = field.data
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        raise ValidationError(
            'Username must be 3-20 characters and can only contain letters, numbers, and underscores.'
        )


def validate_video_url(form, field):
    """Custom validator for video URLs (YouTube, Vimeo, or direct MP4)."""
    url = field.data
    if url:
        youtube_pattern = r'(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)'
        vimeo_pattern = r'vimeo\.com/'
        mp4_pattern = r'\.mp4$|\.webm$'

        if not (
            re.search(youtube_pattern, url)
            or re.search(vimeo_pattern, url)
            or re.search(mp4_pattern, url)
        ):
            raise ValidationError('Please enter a valid YouTube, Vimeo, or direct video URL.')


def validate_image_url(form, field):
    """Custom validator for image URLs."""
    url = field.data
    if url:
        image_pattern = r'\.(jpg|jpeg|png|gif|webp|svg)(\?.*)?$'
        if not re.search(image_pattern, url, re.IGNORECASE):
            raise ValidationError(
                'Please enter a valid image URL (JPG, PNG, GIF, WEBP, SVG).'
            )


def validate_file_size(form, field):
    """Validate file size (max 16MB by default)."""
    if field.data:
        try:
            if hasattr(field.data, 'seek') and hasattr(field.data, 'tell'):
                field.data.seek(0, 2)
                size = field.data.tell()
                field.data.seek(0)
                max_size = 16 * 1024 * 1024
                if size > max_size:
                    raise ValidationError('File size must be less than 16MB.')
            elif hasattr(field.data, 'content_length'):
                size = field.data.content_length
                max_size = 16 * 1024 * 1024
                if size > max_size:
                    raise ValidationError('File size must be less than 16MB.')
        except ValidationError:
            raise
        except Exception:
            # Ignore validation errors from non-file objects
            pass
    return True


def validate_terms(form, field):
    """Custom validator for terms checkbox (DataRequired doesn't work well with checkboxes)."""
    if not field.data:
        raise ValidationError('You must agree to the terms and conditions to register.')


# ==================== CUSTOM FILE FIELD ====================

class ValidatedFileField(FileField):
    """File field with size validation."""

    def __init__(self, label=None, validators=None, max_size_mb=16, **kwargs):
        super().__init__(label, validators, **kwargs)
        self.max_size_mb = max_size_mb

    def pre_validate(self, form):
        super().pre_validate(form)
        if self.data:
            if hasattr(self.data, 'seek') or hasattr(self.data, 'content_length'):
                validate_file_size(form, self)


# ==================== AUTH FORMS ====================

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=80, message='Username must be between 3 and 80 characters.'),
        validate_username
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message='Email address is required.'),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    is_instructor = BooleanField('Register as Instructor')
    terms_agreed = BooleanField(
        'I agree to the Terms and Conditions',
        validators=[validate_terms]
    )
    submit = SubmitField('Create Account')


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message='Email address is required.'),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class PasswordChangeForm(FlaskForm):
    """Change password form for authenticated users."""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required.')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required.'),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password.'),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Change Password')


class PasswordResetRequestForm(FlaskForm):
    """Password reset request form."""
    email = StringField('Email Address', validators=[
        DataRequired(message='Please enter your email address.'),
        Email(message='Please enter a valid email address.')
    ])
    submit = SubmitField('Send Reset Link')


class PasswordResetForm(FlaskForm):
    """Password reset form (after clicking reset link)."""
    password = PasswordField('New Password', validators=[
        DataRequired(message='Please enter a new password.'),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Reset Password')


# ==================== COURSE & LESSON FORMS ====================

class CourseForm(FlaskForm):
    title = StringField('Course Title', validators=[
        DataRequired(message='Course title is required.'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters.')
    ])
    description = TextAreaField('Course Description', validators=[
        DataRequired(message='Course description is required.'),
        Length(min=20, max=5000, message='Description must be between 20 and 5000 characters.')
    ])
    price = FloatField('Price ($)', validators=[
        Optional(),                                    # ✅ DataRequired hata diya
        NumberRange(min=0, max=9999, message='Price must be between $0 and $9,999.')
    ], default=0.0)
    image = ValidatedFileField('Course Image (Upload from computer)', validators=[
        FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'webp'],
                    'Only JPG, PNG, GIF, and WEBP images are allowed.')
    ], max_size_mb=16)
    image_url = StringField('Image URL (Optional)', validators=[
        Optional(),
        URL(message='Please enter a valid URL.'),
        validate_image_url
    ])
    category = SelectField('Category', choices=[
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
    ], validators=[DataRequired(message='Please select a category.')], default='programming')
    level = SelectField('Level', choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels')
    ], validators=[DataRequired(message='Please select a level.')], default='beginner')
    submit = SubmitField('Create Course')


class LessonForm(FlaskForm):
    title = StringField('Lesson Title', validators=[
        DataRequired(message='Lesson title is required.'),
        Length(min=3, max=200, message='Title must be between 3 and 200 characters.')
    ])
    content = TextAreaField('Lesson Content', validators=[
        DataRequired(message='Lesson content is required.'),
        Length(min=10, max=10000, message='Content must be between 10 and 10000 characters.')
    ])
    video_url = StringField('Video URL (YouTube, Vimeo, or direct MP4)', validators=[
        Optional(),
        validate_video_url
    ])
    order = IntegerField('Lesson Order', validators=[
        DataRequired(message='Lesson order is required.'),
        NumberRange(min=1, max=999, message='Order must be between 1 and 999.')
    ], default=1)
    duration_minutes = IntegerField('Duration (minutes)', validators=[
        Optional(),
        NumberRange(min=1, max=300, message='Duration must be between 1 and 300 minutes.')
    ], default=10)
    submit = SubmitField('Add Lesson')


# ==================== PROFILE FORMS ====================

class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        Optional(),
        Length(max=120, message='Full name cannot exceed 120 characters.')
    ])
    bio = TextAreaField('Bio', validators=[
        Optional(),
        Length(max=500, message='Bio cannot exceed 500 characters.')
    ])
    location = StringField('Location', validators=[
        Optional(),
        Length(max=100, message='Location cannot exceed 100 characters.')
    ])
    website = StringField('Website', validators=[
        Optional(),
        URL(message='Please enter a valid URL (e.g., https://example.com).'),
        Length(max=200)
    ])
    occupation = StringField('Occupation', validators=[
        Optional(),
        Length(max=100)
    ])
    education = StringField('Education', validators=[
        Optional(),
        Length(max=200)
    ])
    skills = TextAreaField('Skills (comma-separated)', validators=[
        Optional(),
        Length(max=500, message='Skills list cannot exceed 500 characters.')
    ])
    social_twitter = StringField('Twitter URL', validators=[
        Optional(),
        URL(message='Please enter a valid Twitter URL.'),
        Length(max=200)
    ])
    social_linkedin = StringField('LinkedIn URL', validators=[
        Optional(),
        URL(message='Please enter a valid LinkedIn URL.'),
        Length(max=200)
    ])
    social_github = StringField('GitHub URL', validators=[
        Optional(),
        URL(message='Please enter a valid GitHub URL.'),
        Length(max=200)
    ])
    submit = SubmitField('Save Changes')


class AvatarForm(FlaskForm):
    avatar = ValidatedFileField('Profile Picture', validators=[
        FileRequired(message='Please select an image file.'),
        FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'webp'],
                    'Only JPG, PNG, GIF, and WEBP images are allowed.')
    ], max_size_mb=5)
    submit = SubmitField('Upload Avatar')


# ==================== REVIEW / SEARCH / CONTACT ====================

class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        (5, '★★★★★ - Excellent'),
        (4, '★★★★☆ - Very Good'),
        (3, '★★★☆☆ - Good'),
        (2, '★★☆☆☆ - Fair'),
        (1, '★☆☆☆☆ - Poor')
    ], validators=[DataRequired(message='Please select a rating.')], coerce=int)
    comment = TextAreaField('Your Review', validators=[
        Optional(),
        Length(max=1000, message='Review cannot exceed 1000 characters.')
    ])
    submit = SubmitField('Submit Review')


class SearchForm(FlaskForm):
    """Search form for courses."""
    query = StringField('Search', validators=[
        Optional(),
        Length(min=2, max=100, message='Search term must be between 2 and 100 characters.')
    ])
    category = SelectField('Category', choices=[
        ('', 'All Categories'),
        ('programming', 'Programming'),
        ('webdev', 'Web Development'),
        ('business', 'Business'),
        ('design', 'Design'),
        ('datascience', 'Data Science'),
        ('marketing', 'Marketing'),
        ('photography', 'Photography'),
        ('music', 'Music'),
        ('language', 'Language Learning')
    ], validators=[Optional()])
    level = SelectField('Level', choices=[
        ('', 'All Levels'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels')
    ], validators=[Optional()])
    sort_by = SelectField('Sort By', choices=[
        ('newest', 'Newest First'),
        ('popular', 'Most Popular'),
        ('rating', 'Highest Rated'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low')
    ], default='newest')
    min_price = FloatField('Min Price', validators=[
        Optional(),
        NumberRange(min=0, message='Minimum price cannot be negative.')
    ])
    max_price = FloatField('Max Price', validators=[
        Optional(),
        NumberRange(min=0, message='Maximum price cannot be negative.')
    ])
    submit = SubmitField('Search')


class ContactForm(FlaskForm):
    """Contact form for user inquiries."""
    name = StringField('Your Name', validators=[
        DataRequired(message='Please enter your name.'),
        Length(max=100)
    ])
    email = StringField('Your Email', validators=[
        DataRequired(message='Please enter your email.'),
        Email(message='Please enter a valid email address.')
    ])
    subject = StringField('Subject', validators=[
        DataRequired(message='Please enter a subject.'),
        Length(max=200)
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(message='Please enter your message.'),
        Length(min=10, max=5000, message='Message must be between 10 and 5000 characters.')
    ])
    submit = SubmitField('Send Message')


class NewsletterForm(FlaskForm):
    """Newsletter subscription form."""
    email = StringField('Email Address', validators=[
        DataRequired(message='Please enter your email address.'),
        Email(message='Please enter a valid email address.')
    ])
    submit = SubmitField('Subscribe')


# ==================== QUIZ FORMS ====================

class QuizForm(FlaskForm):
    """Form for creating/editing quiz questions."""
    question = TextAreaField('Question', validators=[
        DataRequired(message='Question is required.'),
        Length(min=5, max=500, message='Question must be between 5 and 500 characters.')
    ])
    option_a = StringField('Option A', validators=[
        DataRequired(message='Option A is required.'),
        Length(max=200)
    ])
    option_b = StringField('Option B', validators=[
        DataRequired(message='Option B is required.'),
        Length(max=200)
    ])
    option_c = StringField('Option C', validators=[
        DataRequired(message='Option C is required.'),
        Length(max=200)
    ])
    option_d = StringField('Option D', validators=[
        DataRequired(message='Option D is required.'),
        Length(max=200)
    ])
    correct_answer = SelectField('Correct Answer', choices=[
        ('a', 'Option A'),
        ('b', 'Option B'),
        ('c', 'Option C'),
        ('d', 'Option D')
    ], validators=[DataRequired(message='Please select the correct answer.')])
    points = IntegerField('Points', validators=[
        DataRequired(message='Points are required.'),
        NumberRange(min=1, max=100, message='Points must be between 1 and 100.')
    ], default=10)
    explanation = TextAreaField('Explanation (Optional)', validators=[
        Optional(),
        Length(max=500, message='Explanation cannot exceed 500 characters.')
    ])
    submit = SubmitField('Save Question')


# ==================== FILTER FORMS ====================

class CourseFilterForm(FlaskForm):
    """Advanced course filtering form."""
    category = SelectField('Category', choices=[
        ('all', 'All Categories'),
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
    ], default='all')
    level = SelectField('Level', choices=[
        ('all', 'All Levels'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels')
    ], default='all')
    price_range = SelectField('Price Range', choices=[
        ('all', 'All Prices'),
        ('free', 'Free'),
        ('paid', 'Paid Only'),
        ('under_50', 'Under $50'),
        ('50_100', '$50 - $100'),
        ('over_100', 'Over $100')
    ], default='all')
    sort_by = SelectField('Sort By', choices=[
        ('newest', 'Newest First'),
        ('popular', 'Most Popular'),
        ('rating', 'Highest Rated'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low')
    ], default='newest')
    submit = SubmitField('Apply Filters')


# ==================== ADMIN FORMS ====================

class AdminUserForm(FlaskForm):
    """Admin form for creating/editing users."""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=80),
        validate_username
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required.'),
        Email(message='Please enter a valid email.')
    ])
    password = PasswordField('Password', validators=[
        Optional(),
        Length(min=6, message='Password must be at least 6 characters.')
    ])
    is_instructor = BooleanField('Instructor Status')
    is_admin = BooleanField('Admin Status')
    full_name = StringField('Full Name', validators=[Optional(), Length(max=120)])
    submit = SubmitField('Save User')


class CertificateForm(FlaskForm):
    """Form for generating certificates."""
    certificate_id = HiddenField()
    download_format = SelectField('Download Format', choices=[
        ('pdf', 'PDF Document'),
        ('png', 'PNG Image')
    ], default='pdf')
    include_signature = BooleanField('Include Digital Signature', default=True)
    submit = SubmitField('Generate Certificate')


# ==================== HELPER FUNCTIONS ====================

def get_category_choices():
    """Return list of category choices."""
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


def get_level_choices():
    """Return list of level choices."""
    return [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels')
    ]