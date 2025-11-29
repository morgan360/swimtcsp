# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TCSP (Templeogue College Swimming Pool) is a Django 5.2.2-based booking and management platform for a swimming pool business. The platform handles public lesson bookings, public swim sessions, school swimming programs, payment processing via Bank of Ireland Payment API (BOIPA), user management, attendance tracking, and financial reconciliation.

**Deployment:** PythonAnywhere (cloud hosting)
**Database:** MySQL
**Frontend:** Tailwind CSS 3.4.7 + DaisyUI + Alpine.js + HTMX

## Development Commands

### Setup and Running
```bash
# Virtual environment (use .venv or venv)
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt

# Database migrations
python manage.py migrate

# Run development server
python manage.py runserver

# Frontend build (Tailwind CSS)
npm install
npm run build  # Watches ./static/src/input.css and rebuilds on changes (continuous)

# Collect static files (for production)
python manage.py collectstatic
```

### Testing
```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test lessons_bookings

# Run specific test case
python manage.py test lessons_bookings.tests.TestTermPhases

# Run specific test method
python manage.py test lessons_bookings.tests.TestTermPhases.test_specific_method

# Run with verbose output
python manage.py test --verbosity=2

# Keep test database for inspection
python manage.py test --keepdb
```

### Useful Management Commands
```bash
# Create superuser
python manage.py createsuperuser

# Shell with Django context
python manage.py shell

# Show URLs
python manage.py show_urls  # Requires django_extensions

# Database shell
python manage.py dbshell
```

### Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions to PythonAnywhere.

Quick deploy to dev server:
```bash
./deploy-to-dev.sh
```

## Architecture Overview

### Multi-Environment Settings
Settings are split across multiple files in `/config/`:
- `base_settings.py` - Shared configuration
- `development_settings.py` - Development environment
- `local_settings.py` - Local development overrides
- `production_settings.py` - Production deployment

The active settings module is determined by the `DJANGO_SETTINGS_MODULE` variable in `.env`.

### Core Django Apps (38 total)

**Primary Booking Flow:**
- `lessons/` - Lesson definitions (Product model with categories, programs)
- `lessons_bookings/` - Booking logic, Term management, LessonEnrollment
- `lessons_orders/` - Order and payment processing for lessons

**Public Swims:**
- `swims/` - Public swim session configuration (PublicSwimProduct)
- `swims_orders/` - Checkout and order handling for swim sessions

**School Programs:**
- `schools/` - School swimming program setup (ScoSchool, ScoLessons)
- `schools_bookings/` - Booking interface for school groups
- `schools_orders/` - School payment/order processing

**User Management:**
- `users/` - Custom user model (email-based authentication), Swimling (swimmer profiles)
- `dashboard/` - Admin dashboard views
- `swimling_dashboard/` - Guardian/parent dashboard for managing swimmers

**Supporting Systems:**
- `shopping_cart/` - Unified shopping cart logic (handles lessons & school bookings)
- `boipa/` - Bank of Ireland Payment API integration
- `waiting_list/` - Waitlist management for fully booked classes
- `coupons/` - Discount coupon system
- `timetable/` - Class/event scheduling
- `reports/` - Custom reporting and data exports
- `finances/` - Financial reconciliation and reporting
- `navigation/` - Dynamic navigation menu system
- `progress/` - Student progress tracking
- `instructors/` - Instructor management
- `anseo/` - Attendance tracking ("anseo" is Irish for "present")
- `chatbot/` - AI-powered FAQ chatbot (OpenAI integration)
- `mailchimp/` - Mailchimp email marketing integration

**Infrastructure:**
- `custom_admins/` - 8 specialized admin panels (not just one)
- `utils/` - Shared utilities (context processors, middleware, date helpers)
- `theme/` - Tailwind theme setup and base templates

### Custom Admin Sites

Instead of using a single Django admin interface, the project has **9 specialized admin panels**:
- `/admin/` - Main Django admin
- `/lessonsadmin/` - Lesson management
- `/usersadmin/` - User management
- `/swimsadmin/` - Swim session management
- `/schoolsadmin/` - School program management
- `/generaladmin/` - General admin tasks
- `/instructorsadmin/` - Instructor management
- `/couponsadmin/` - Coupon management
- `/attendanceadmin/` - Attendance tracking
- `/finance-admin/` - Financial reconciliation

Each admin site is customized in the `/custom_admins/` directory with its own configuration.

## Key Architecture Patterns

### 1. Term-Based Booking System
The entire platform operates on **terms** (school term periods):
- Terms have start/end dates, booking open dates, and rebooking dates
- Three booking phases: **BK** (Before Booking), **RB** (Rebooking Priority), **BN** (Booking Open)
- Context processor `get_term_info` provides term state globally to all templates
- All lesson enrollments are linked to specific terms

**Enrollment Chain:** Swimling → Lesson (Product) → Term → Order

### 2. Multi-Tenant Shopping Cart
The shopping cart (`/shopping_cart/cart.py`) supports two distinct product types:
- `'lesson'` - Public lesson bookings
- `'school'` - School program bookings
- Cart automatically clears when switching between types
- Cart items are session-based using Django's session framework

### 3. Payment Flow
Standard e-commerce flow with external payment gateway:
1. User adds items to cart
2. Cart creates an Order (LessonOrder, SwimOrder, or SchoolOrder)
3. Order is sent to BOIPA payment gateway
4. Payment notification webhook updates order status
5. On payment success, creates LessonEnrollment records

### 4. Custom User Model
- Email-based authentication (no username field)
- Uses Django Allauth for authentication
- Supports Google OAuth via `allauth.socialaccount.providers.google`
- **Swimling** model represents individual swimmers linked to guardian (User)

### 5. Signal-Based Auto-Generation
Many models use Django signals for automatic field generation:
```python
@receiver(pre_save, sender=Product)
def auto_generate_name(sender, instance, **kwargs):
    # Auto-generate product names from category + day + time
```

Common patterns:
- Product names auto-generated from components
- Slugs auto-generated from names
- Order numbers generated on creation

## Important Data Models

### Users & Profiles
- `User` (custom user model) - Email-based, no username
- `Swimling` - Swimmer profile linked to a guardian User

### Lessons
- `Program` → `Category` → `Product` (lesson class hierarchy)
- `Term` - School term with booking phases (BK, RB, BN)
- `LessonEnrollment` - Confirmed booking (Swimling + Lesson + Term + Order)
- `LessonAssignment` - Links instructors to lessons

### Orders
- `Order` - Parent order model (lessons, swims, schools)
- `OrderItem` - Individual line items in an order
- Links to BOIPA payment notifications via webhooks

### Schools
- `ScoSchool` - School information
- `ScoTerm` - School-specific terms
- `ScoLessons` - School lesson definitions
- Similar enrollment pattern to public lessons

## Frontend Patterns

### HTMX-Driven Interactivity
- Dynamic content loading without full page refreshes
- Used for cart updates, filters, search results
- Endpoints return HTML partials, not JSON

### Alpine.js State Management
- Lightweight reactive components
- Manages UI state (drawers, modals, dropdowns)
- No heavy JavaScript framework required

### DataTables Integration
- Interactive tables with Bootstrap 5 styling
- Responsive design with export buttons (CSV, Excel, PDF)
- Used for admin reports and data-heavy views

### Template Inheritance
- Base template: `/templates/base/_base.html`
- Extends with blocks: `{% block title %}`, `{% block content %}`, etc.
- Partials in `/templates/partials/` (navbar, drawer, footer)

### Global Context Processors
Available in all templates via `/utils/context_processors.py`:
- `get_term_info` - Current term state and booking phase
- `term_status_for_active_schools` - School term status
- `footer_message` - Environment indicator (dev/prod)

## Important Conventions

### URL Patterns
- Use kebab-case: `/lessons/book-lesson/`
- Each app manages its own `urls.py`
- Main routing in `/core/urls.py`

### Naming Conventions
- Models: `PascalCase` (e.g., `LessonEnrollment`)
- Views: `snake_case` functions or `PascalCase` classes
- Templates: `snake_case.html`
- App names: `snake_case`

### Standard Django App Structure
```
app_name/
├── migrations/
├── templates/app_name/
├── __init__.py
├── admin.py          # Django admin registration
├── apps.py           # App configuration
├── models.py         # Database models
├── views.py          # View logic
├── urls.py           # URL routing
├── forms.py          # Form definitions
└── tests.py          # Unit tests
```

### Security Practices
- CSRF protection enabled site-wide
- Session-based authentication
- Hijack package for admin user impersonation (auditable)
- Maintenance mode with IP whitelisting
- Rate limiting on login attempts (via django-allauth)

## Working with This Codebase

### Local Development Workflow
1. Activate virtual environment
2. Ensure `.env` file is configured (use `.env.example` as template)
3. Run migrations if models changed
4. Start Django dev server on default port 8000
5. In separate terminal, run `npm run build` for Tailwind watch mode
6. Access site at `http://localhost:8000`

### Making Changes to Models
1. Edit model in `models.py`
2. Create migration: `python manage.py makemigrations`
3. Review migration file in `migrations/` folder
4. Apply migration: `python manage.py migrate`

### Adding New Features
- **Always prefer editing existing files over creating new ones**
- Follow existing patterns in the app you're modifying
- If adding a new model, register it in `admin.py` or appropriate custom admin
- If adding views, create corresponding URL patterns
- Update templates to reflect new functionality

### Understanding Term Phases
When working with booking logic, understand the three phases:
- **BK (Before Booking)**: Term exists but booking not yet open
- **RB (Rebooking)**: Priority booking for existing members
- **BN (Booking Open)**: General booking open to all

Check current phase using context processor data in templates.

### Static Files
- Source files: `/static/`
- Tailwind input: `/static/src/input.css`
- Built CSS: `/static/css/styles.css` (generated by Tailwind)
- Production collected files: `/static_files/` (not in git)
- Run `collectstatic` before deploying

### Environment Variables
Key variables in `.env`:
- `DEBUG` - Enable debug mode
- `SECRET_KEY` - Django secret key
- `DB_PASSWORD` - MySQL database password
- `DJANGO_SETTINGS_MODULE` - Which settings file to use
- `BOIPA_API_KEY` - Payment gateway API key

## Common Development Tasks

### Testing Changes to Booking Flow
1. Create test user and swimling
2. Ensure current term is active with correct phase
3. Add lessons to cart
4. Proceed through checkout (use test payment credentials)
5. Verify enrollment created and appears in dashboard

### Debugging Payment Issues
1. Check BOIPA webhook logs in `/logs/`
2. Verify order status in admin
3. Check `Order` and `OrderItem` records
4. Confirm BOIPA payment notification received

### Working with Admin Sites
- Each admin site has its own URL namespace
- Custom admin classes in `/custom_admins/admin_*.py`
- Register models in appropriate admin site, not just default admin

### Database Queries
- Use Django ORM exclusively (no raw SQL unless necessary)
- Leverage `select_related()` and `prefetch_related()` for performance
- Use `.filter()` chains for readability

## Documentation Resources

- Full developer docs: `/docs/legacy_notes/README.md`
- Architecture details in various `/docs/*.md` files
- Repository: https://github.com/morgan360/swimtcsp

## Key Third-Party Packages

- **django-allauth**: Authentication with social providers
- **django-crispy-forms**: Form rendering
- **django-import-export**: CSV/Excel data import/export
- **django-hijack**: Admin user impersonation
- **django-filter**: Filtering querysets
- **phonenumber-field**: Phone number validation
- **ReportLab / WeasyPrint**: PDF generation
- **OpenAI**: Chatbot functionality
