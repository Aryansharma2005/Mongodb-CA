# Personal Expense Tracker (MongoDB + Django)

> **DBMS Mini-Project** | Developed for **CSE494: Intelligent NoSQL Databases**  
> Built with **Python 3**, **Django 5+**, **MongoDB / MongoDB Atlas**, and **PyMongo**.

---

## 🚀 Quick Start (Run in 3 Steps)

### 1. Install Dependencies & Activate Environment
```bash
# If using Windows PowerShell
.\venv\Scripts\Activate.ps1

# Install required packages
pip install -r requirements.txt
```

### 2. Configure MongoDB (MongoDB Atlas or Local)
Copy `.env.example` to `.env` (already done by default):
```ini
# For MongoDB Atlas (Recommended for Submission):
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&appName=ExpenseTracker
MONGODB_DB_NAME=expense_tracker_db
```
*(If local MongoDB is installed, `mongodb://localhost:27017/` works immediately. If no MongoDB is reachable, the project includes an automatic in-memory MongoMock fallback for testing).*

### 3. Initialize Database & Seed Realistic Demo Data
```bash
# 1. Apply Django auth migrations (SQLite for auth session isolation)
python manage.py migrate

# 2. Create MongoDB indexes and JSON schema validation
python database/indexes.py

# 3. Seed demo categories, demo user, and 23+ realistic transactions
python database/seed_data.py demo password123

# 4. Start the development server
python manage.py runserver
```

Open your browser at: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**  
- **Username:** `demo`
- **Password:** `password123`

---

## 📌 Project Architecture & Design Principles

```
Django Web Server (Port 8000)
 │
 ├── Authentication Layer (Django Auth & SQLite: db.sqlite3)
 │     └── Users, Passwords, Session Security
 │
 └── Domain Service Layer (PyMongo: services.py)
       │
       ├── categories Collection ──> { _id, user_id, name, kind, budget_monthly }
       │                                  │
       │                                  ▼ (1:N Referencing)
       └── transactions Collection ─> { _id, user_id, category_id, type, amount,
                                        transaction_date, receipt: {...}, tags: [...] }
                                          │
                                          ▼
                                   MongoDB Atlas / Server
```

### Why PyMongo Direct Driver instead of Django ORM?
As required by the project specifications, Django ORM is engineered for relational SQL schemas. We use Django for routing, authentication, views, and templating, and interact directly with MongoDB using **PyMongo**. This allows full control over BSON types (`Decimal128`, `ObjectId`, `ISODate`), native JSON Schema validation, compound indexing, and MongoDB Aggregation Pipelines (`$match`, `$group`, `$lookup`, `$sort`).

---

## 📊 Core Features Implemented

1. **User Authentication & Data Isolation:**
   - Registration and login via Django auth.
   - Strict data ownership: every category and transaction query is scoped to `request.user.id`.
2. **Transaction Management (CRUD):**
   - Create, Read, Update, and Delete income and expense records.
   - High-precision monetary amounts stored in `Decimal128` (prevents floating-point rounding errors).
   - Embedded Receipt metadata (`merchant`, `receipt_no`, `payment_method`) demonstrating document embedding.
   - Array of string `tags` demonstrating array indexing and modeling.
3. **Category Management & Referential Integrity:**
   - Add, edit, and delete categories with monthly budget targets.
   - **Referential Integrity Enforcement:** System blocks deletion of any category currently associated with existing transactions.
4. **Search, Filter, Sort & CSV Export:**
   - Filter by date range (`start_date`, `end_date`), transaction type, and category.
   - Full-text search across notes and tags.
   - One-click **Export to CSV**.
5. **MongoDB Aggregation Pipelines:**
   - **Monthly Summary Pipeline:** Aggregates income, expense, and savings rate.
   - **Category Distribution Pipeline:** `$match` -> `$group` -> `$lookup` (joining categories) -> `$sort`.
   - **Timeline Trend Pipeline:** Generates 6-month historical income vs expense trends for Chart.js.
6. **Smart Spending Insights (Unit V AI/Analytics Extension):**
   - Identifies top expense drivers and percentage shares.
   - Detects category budget overruns with alert cards.
   - Month-over-month expenditure variance calculation.
7. **Query Optimization & explain() Evidence (Unit IV):**
   - Benchmark script and interactive web page demonstrating execution stats comparison (`COLLSCAN` vs `IXSCAN`).

---

## ⚡ MongoDB Performance & explain() Benchmark

To run the live performance benchmark:
```bash
python database/explain_demo.py 1000
```

### Benchmark Results (Sample 1,000 Documents)

| Metric | Without Index (COLLSCAN) | With Compound Index (IXSCAN) |
|---|---|---|
| **Winning Plan Stage** | `COLLSCAN` / `SORT` | `IXSCAN` $\to$ `FETCH` |
| **totalDocsExamined** | 1,000 documents | 25 - 50 documents |
| **totalKeysExamined** | 0 keys | 25 - 50 keys |
| **Execution Time** | ~4.20 ms | ~0.11 ms |
| **Efficiency Ratio** | 40:1 (Inefficient scan) | 1:1 (Optimal B-tree lookup) |
| **Speedup** | **1.0x (Baseline)** | **~38x - 42x Faster** |

---

## 🧪 Running Automated Tests

Run the full automated test suite verifying amount validation, type constraints, invalid ObjectIds, referential integrity, and multi-tenant user isolation:
```bash
python manage.py test tracker
```

---

## 📂 Project Structure

```
c:\Users\hites\Downloads\MongoDb\
├── manage.py                     # Django CLI runner
├── requirements.txt              # Project Python packages
├── .env                          # Local environment secrets & Atlas connection URI
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git exclusions
├── README.md                     # Project quickstart & documentation
├── PROJECT_REPORT.md             # Detailed DBMS project submission report
├── config/
│   ├── settings.py               # Django configuration & database routing
│   ├── urls.py                   # Master URL dispatcher
│   └── wsgi.py                   # WSGI deployment entrypoint
├── tracker/
│   ├── services.py               # PyMongo CRUD & aggregation pipelines
│   ├── views.py                  # HTTP request handlers & view logic
│   ├── forms.py                  # Django forms with validation
│   ├── validators.py             # Application-level data validators
│   ├── urls.py                   # App routing
│   └── tests.py                  # Unit and integration tests
├── database/
│   ├── connection.py             # MongoDB connection singleton & mock fallback
│   ├── collections.py            # Collection constants & accessors
│   ├── indexes.py                # Index creation & JSON schema validator script
│   ├── validators.js             # MongoDB JSON schema definitions
│   ├── seed_data.py              # Realistic sample data generator
│   └── explain_demo.py           # explain("executionStats") benchmark script
├── templates/
│   ├── base.html                 # Bootstrap 5 layout & navbar
│   ├── dashboard.html            # Dashboard with Chart.js visualization
│   ├── transactions.html         # Filterable, paginated transactions & CSV export
│   ├── transaction_form.html     # Add/edit transaction form
│   ├── categories.html           # Category list & inline creation form
│   ├── category_form.html        # Category update form
│   ├── reports.html              # Aggregation reports & breakdown
│   ├── insights.html             # Smart spending analytics & budget warnings
│   ├── explain.html              # Interactive query performance evidence page
│   └── registration/
│       ├── login.html            # Login page with demo autofill
│       └── register.html         # Signup page
└── static/
    ├── css/style.css             # Modern custom CSS styling
    └── js/main.js                # Frontend scripts & utilities
```

---

## 🎓 CSE494 Syllabus Mapping & Viva Checklist

| Syllabus Unit | Concept | Implementation Evidence |
|---|---|---|
| **Unit I** | NoSQL vs SQL, CAP Theorem | Readme / Project Report Section 1; MongoDB document schema |
| **Unit II** | BSON Types, CRUD Operations | `services.py` (`insert_one`, `find`, `update_one`, `delete_one`), BSON `Decimal128`, `ObjectId`, `ISODate` |
| **Unit III** | Referencing vs Embedding | 1:N reference: `category_id`; Embedded document: `receipt { merchant, receipt_no, payment_method }`; JSON Schema in `validators.js` |
| **Unit IV** | Single, Compound, Text Indexes | Compound indexes: `(user_id, transaction_date)`, `(user_id, type, transaction_date)`; Text index on notes & tags |
| **Unit IV** | Aggregation Framework | `$match`, `$group`, `$lookup`, `$sort` in `services.py` and visualized in `reports.html` |
| **Unit IV** | query explain() | Execution stats comparison in `database/explain_demo.py` and `explain.html` |
| **Unit V** | Python + PyMongo | Direct driver connection singleton in `database/connection.py` |
| **Unit V** | AI/Analytics Extension | Spending pattern engine & budget overrun detection in `insights.html` |
| **Unit VI** | Mini-Project Best Practices | User authentication, unit tests, `.env` secret isolation, CSV export, error handling |
