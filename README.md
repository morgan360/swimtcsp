
# TCSP Swimming Pool Booking Platform

This is a Django-based web application designed for managing lessons, swims, schools, and online bookings for a swimming pool business. It includes user registration, e-commerce integration with Bank of Ireland Finance, custom admin dashboards, and HTMX/Tailwind/Alpine-based interactivity.

---
📚 Looking for full developer documentation?
See [docs/README.md](docs/README.md) for:
- Architecture
- Deployment (PythonAnywhere)
- Tailwind/HTMX frontend setup
- Git logs and to-dos



## 🌐 Live Features Overview

- User login, profile, and group management
- Public class browsing and booking (lessons, swims, schools)
- Waiting list management for oversubscribed classes
- Shopping cart and checkout
- BOIPA (Bank of Ireland) payment processing
- Custom reports, admin panels, and scheduling

---

## 🧱 App Structure

| App | Purpose |
|-----|---------|
| **home** | Public homepage and landing views |
| **users** | Registration, authentication, profile management |
| **lessons** | Lesson definitions, filters, and availability |
| **lessons_bookings** | Booking logic and forms for lessons |
| **lessons_orders** | Order/payment handling for lesson bookings |
| **swims** | Public swim session configuration |
| **swims_orders** | Checkout and logic for swim sessions |
| **schools** | School swimming program setup |
| **schools_bookings** | Booking interface for school groups |
| **schools_orders** | School payment/order processing |
| **shopping_cart** | Shared shopping cart logic |
| **boipa** | Bank of Ireland payment API integration |
| **reports** | Custom reporting and exports for admins |
| **waiting_list** | Waitlist tracking for full lessons/swims |
| **timetable** | Class/event scheduling system |
| **custom_admins** | Custom admin panels (users, lessons, swims) |
| **theme** | Tailwind theme setup, base templates |
| **mailchimp_integration** | Email marketing sync (e.g., Mailchimp) |
| **import_csv** | CSV imports (data migration notebooks/files) |
| **utils** | Shared utilities: context processors, middleware, dates, etc. |

---

## 🛠 Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/swimming-pool-site.git
   cd swimming-pool-site
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the development server:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

4. **(Optional) Watch for Tailwind changes:**
   ```bash
   npm install
   npm run dev
   ```

---

## 🔑 Environment Variables

Your `.env` file should include:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=mysql://...
BOIPA_API_KEY=...
```

---

## 🧪 Testing

```bash
python manage.py test
```

---

## 📦 Deployment

You are deploying to [PythonAnywhere](https://www.pythonanywhere.com/) via GitHub. Follow their WSGI and static files configuration. A `production_settings.py` file is available for use on your live server.

---

## 📁 Docs

Additional notes and developer documentation are in the `/docs` folder:
- `README.md` (this file)
- `to-do-list.md` – current backlog
- `accounts.md`, `apps.md`, `admin.md` – feature-specific notes
- CSV files for mass data import (`/import_csv/`)

---

## 📬 Contact

For development or support:  
📧 [Your Email or Team Email]  
🔗 [https://your-live-site.com](https://your-live-site.com)
