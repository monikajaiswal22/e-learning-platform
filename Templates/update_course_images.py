"""
Course Image Updater Script
Run this script to update course images from various sources.
Usage: python update_course_images.py
"""

import os
import sys
import random
import requests
from pathlib import Path

# Add parent directory to path if running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Course

# High-quality course image URLs from Unsplash (organized by category)
COURSE_IMAGES = {
    # Programming & Coding
    'programming': [
        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6",  # Coding on screen
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c",  # Code editor
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97",  # Laptop with code
        "https://images.unsplash.com/photo-1587620962725-abab7fe55159",  # Programming concept
        "https://images.unsplash.com/photo-1542831371-29b0f74f9713",  # Code on monitor
    ],
    # Web Development
    'webdev': [
        "https://images.unsplash.com/photo-1516116216624-53e697fedbea",  # Web design
        "https://images.unsplash.com/photo-1547658719-da2b51169166",  # Responsive design
        "https://images.unsplash.com/photo-1498050108023-c5249f4df085",  # Laptop coding
        "https://images.unsplash.com/photo-1581291518633-83b4ebd1d83e",  # Web development
    ],
    # Business & Marketing
    'business': [
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40",  # Business meeting
        "https://images.unsplash.com/photo-1557804506-669a67965ba0",  # Business graph
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf",  # Business strategy
        "https://images.unsplash.com/photo-1551836022-d5d88e9218df",  # Office work
    ],
    # Design & Creative
    'design': [
        "https://images.unsplash.com/photo-1561070791-2526d30994b5",  # Design workspace
        "https://images.unsplash.com/photo-1581291518633-83b4ebd1d83e",  # UI/UX design
        "https://images.unsplash.com/photo-1561070791-2526d30994b5",  # Graphic design
        "https://images.unsplash.com/photo-1547658719-da2b51169166",  # Color palette
    ],
    # Data Science
    'datascience': [
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71",  # Data analytics
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71",  # Big data
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f",  # Data charts
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71",  # Data visualization
    ],
    # General / Default
    'default': [
        "https://images.unsplash.com/photo-1434030216411-0b793f4b4173",  # Learning
        "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45",  # Education
        "https://images.unsplash.com/photo-1523240795612-9a054b0db644",  # Students
        "https://images.unsplash.com/photo-1524178232363-1fb2b075b655",  # Books
    ]
}

# Placeholder images (free, reliable fallbacks)
FALLBACK_IMAGES = [
    "https://via.placeholder.com/800x400?text=Programming+Course",
    "https://via.placeholder.com/800x400?text=Web+Development",
    "https://via.placeholder.com/800x400?text=Data+Science",
    "https://via.placeholder.com/800x400?text=Business+Course",
    "https://via.placeholder.com/800x400?text=Design+Course",
]

def validate_image_url(url):
    """Check if image URL is accessible"""
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False

def get_image_for_course(course_title, category=None):
    """Get appropriate image based on course title/category"""
    title_lower = course_title.lower()
    
    # Determine category based on keywords in title
    if any(word in title_lower for word in ['python', 'java', 'coding', 'programming', 'c++', 'javascript']):
        category = 'programming'
    elif any(word in title_lower for word in ['web', 'html', 'css', 'react', 'angular', 'vue', 'frontend', 'backend']):
        category = 'webdev'
    elif any(word in title_lower for word in ['business', 'marketing', 'management', 'entrepreneur', 'sales']):
        category = 'business'
    elif any(word in title_lower for word in ['design', 'ui', 'ux', 'graphic', 'creative', 'art']):
        category = 'design'
    elif any(word in title_lower for word in ['data', 'analytics', 'machine learning', 'ai', 'statistics']):
        category = 'datascience'
    else:
        category = 'default'
    
    # Get random image from selected category
    images = COURSE_IMAGES.get(category, COURSE_IMAGES['default'])
    return random.choice(images)

def update_single_course(course_id, image_url=None):
    """Update a specific course by ID"""
    with app.app_context():
        course = Course.query.get(course_id)
        if course:
            if image_url is None:
                image_url = get_image_for_course(course.title)
            
            course.image_url = image_url
            db.session.commit()
            print(f"✅ Updated image for course: {course.title}")
            print(f"   Image URL: {image_url[:80]}...")
            return True
        else:
            print(f"❌ Course with ID {course_id} not found")
            return False

def update_courses_without_images(dry_run=False):
    """Update all courses that don't have images"""
    with app.app_context():
        courses_without_images = Course.query.filter(
            (Course.image_url.is_(None)) | (Course.image_url == '')
        ).all()
        
        if not courses_without_images:
            print("✅ All courses already have images!")
            return 0
        
        print(f"\n📚 Found {len(courses_without_images)} courses without images\n")
        
        updated_count = 0
        for idx, course in enumerate(courses_without_images, 1):
            image_url = get_image_for_course(course.title)
            
            # Optional: Validate URL (skip if slow)
            # if not validate_image_url(image_url):
            #     image_url = random.choice(FALLBACK_IMAGES)
            
            if not dry_run:
                course.image_url = image_url
                print(f"  {idx}. ✅ {course.title[:50]}...")
            else:
                print(f"  {idx}. 🔍 Would update: {course.title[:50]}...")
            
            updated_count += 1
        
        if not dry_run:
            db.session.commit()
            print(f"\n✨ Successfully updated {updated_count} courses!")
        else:
            print(f"\n🔍 Dry run: Would update {updated_count} courses")
        
        return updated_count

def update_all_courses():
    """Update EVERY course with new images"""
    with app.app_context():
        all_courses = Course.query.all()
        
        if not all_courses:
            print("❌ No courses found in database")
            return 0
        
        print(f"\n📚 Found {len(all_courses)} total courses\n")
        
        updated_count = 0
        for idx, course in enumerate(all_courses, 1):
            image_url = get_image_for_course(course.title)
            course.image_url = image_url
            print(f"  {idx}. ✅ Updated: {course.title[:50]}...")
            updated_count += 1
        
        db.session.commit()
        print(f"\n✨ Successfully updated all {updated_count} courses!")
        return updated_count

def reset_course_images():
    """Reset/remove all course images"""
    with app.app_context():
        confirm = input("⚠️  Are you sure you want to remove ALL course images? (yes/no): ")
        if confirm.lower() == 'yes':
            courses = Course.query.all()
            for course in courses:
                course.image_url = None
            
            db.session.commit()
            print(f"✅ Removed images from {len(courses)} courses")
            return len(courses)
        else:
            print("❌ Operation cancelled")
            return 0

def show_course_images():
    """Display current course images"""
    with app.app_context():
        courses = Course.query.all()
        
        print("\n📸 Current Course Images:\n")
        print("-" * 80)
        for course in courses:
            has_image = "✅" if course.image_url else "❌"
            print(f"{has_image} ID: {course.id:3} | {course.title[:40]:40} | {course.image_url[:50] if course.image_url else 'No image'}")
        print("-" * 80)
        print(f"\nTotal: {len(courses)} courses")
        print(f"With images: {sum(1 for c in courses if c.image_url)}")
        print(f"Without images: {sum(1 for c in courses if not c.image_url)}")

def interactive_menu():
    """Interactive menu for the script"""
    print("\n" + "="*60)
    print("   🖼️  COURSE IMAGE UPDATER")
    print("="*60)
    print("\nOptions:")
    print("  1. Update specific course by ID")
    print("  2. Update courses without images")
    print("  3. Update ALL courses")
    print("  4. Show current course images")
    print("  5. Reset/remove all course images")
    print("  6. Dry run (preview what would be updated)")
    print("  0. Exit")
    
    choice = input("\nEnter your choice (0-6): ").strip()
    
    if choice == '1':
        course_id = input("Enter course ID: ").strip()
        if course_id.isdigit():
            update_single_course(int(course_id))
        else:
            print("❌ Invalid course ID")
    
    elif choice == '2':
        update_courses_without_images()
    
    elif choice == '3':
        confirm = input("⚠️  This will update ALL courses. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            update_all_courses()
    
    elif choice == '4':
        show_course_images()
    
    elif choice == '5':
        reset_course_images()
    
    elif choice == '6':
        update_courses_without_images(dry_run=True)
    
    elif choice == '0':
        print("👋 Goodbye!")
        return False
    
    else:
        print("❌ Invalid choice")
    
    return True

def main():
    """Main execution function"""
    print("\n🎓 E-Learning Platform - Course Image Updater")
    print("=" * 50)
    
    # Check if running in interactive mode
    if len(sys.argv) > 1:
        # Command line arguments
        command = sys.argv[1].lower()
        
        if command == 'all':
            update_all_courses()
        elif command == 'missing':
            update_courses_without_images()
        elif command == 'show':
            show_course_images()
        elif command == 'reset':
            reset_course_images()
        elif command == 'dry-run':
            update_courses_without_images(dry_run=True)
        elif command.isdigit():
            update_single_course(int(command))
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  all      - Update all courses")
            print("  missing  - Update only courses without images")
            print("  show     - Show current course images")
            print("  reset    - Remove all course images")
            print("  dry-run  - Preview what would be updated")
            print("  [ID]     - Update specific course by ID")
    else:
        # Interactive mode
        running = True
        while running:
            running = interactive_menu()
            if running:
                input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()