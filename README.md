# Bristol Regional Food Network – AI Features Demo

**Module:** UFCFUR-15-3 Advanced Artificial Intelligence  
**Group:** 06  
**Implementation:** Parts 3 & 4 – AI Model Management & Explainable Recommendations (Tobias)

---

## Quick Start

### Prerequisites
- Django development server running locally
- Python 3.12 with virtual environment activated
- Superuser account created

### Start the Server
```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Server runs on **http://localhost:8000**

---

## Part 3: AI Model Management Demo

### Step 1 – Create a Mock Model File

Run this command in PowerShell:
```powershell
.venv\Scripts\python -c "import pickle; pickle.dump({'type': 'recommendation_engine', 'version': '1.0'}, open('mock_model.pkl', 'wb')); print('Mock model created!')"
```

This creates `mock_model.pkl` in your project root.

### Step 2 – Login as Staff

1. Go to **http://localhost:8000/admin/**
2. Login with your superuser credentials
3. Click **Users** → select your user
4. Check **"Staff status"** box
5. Click **Save**

### Step 3 – Upload the Model

1. Navigate to **http://localhost:8000/ai/models/**
2. Fill the upload form:
   - **Model Name**: `Rule-based Recommender v1`
   - **Version**: `1.0`
   - **Description**: `Initial rule-based recommendation system`
   - **Model File**: Choose `mock_model.pkl`
   - **Accuracy Score**: `0.82`
   - **Status**: `ACTIVE`
3. Click **Upload Model**

✅ The model appears in the table below with all details displayed.

### Step 4 – Test Model Versioning

Upload a second model:
- **Model Name**: `Rule-based Recommender v2`
- **Version**: `2.0`
- **Description**: `Improved recommendation logic`
- **Model File**: Choose `mock_model.pkl` again
- **Status**: `ACTIVE`

**What happens:** The first model automatically changes to `ARCHIVED` because only one model can be `ACTIVE` at a time.

### Step 5 – Export Activity Data

1. On the `/ai/models/` page, click **"Export Activity Data"**
2. A CSV file downloads with all captured user interactions
3. CSV includes columns: user, action (SEARCH/PRODUCT_VIEW/CART_ADD/etc.), product, search query, timestamp

✅ **Part 3 complete!** The system now tracks user activity and allows model versioning.

---

## Part 4: Admin Dashboard & Explainable Recommendations Demo

### Step 1 – Generate Activity Data

Before viewing the dashboard, create some interaction data:

1. Go to **http://localhost:8000/** (homepage, logout if needed)
2. Search for: `bread`, `honey`, `apples` (logs 3 search actions)
3. Click on 2-3 products (logs product view actions)
4. Add an item to cart (logs cart action)

### Step 2 – View Admin Dashboard

1. Login as superuser again
2. Navigate to **http://localhost:8000/platform/overview/**
3. See the dashboard displaying:
   - **Platform Stats**: Total users, producers, products, low-stock items, recent activity count
   - **Activity Breakdown**: Chart showing action distribution (searches, product views, cart updates, etc.)
   - **Top Searches**: List of most popular search terms
   - **Recent AI Models**: Upload history with model names, versions, accuracy scores
   - **Explainable Recommendations Preview**: Sample recommendations with visible explanations
   - **Recent Activity Log**: Full log of user interactions with timestamps

✅ Dashboard aggregates all data in one superuser view.

### Step 3 – Test Explainable Recommendations on Homepage

1. Go to **http://localhost:8000/** 
2. Scroll down to **"Recommended for You"** section
3. See products with explanation strings like:
   - "Similar to what you viewed recently"
   - "In your preferred category"
   - "Organic certified product"
   - "Currently in stock"

### Step 4 – Test Recommendations on Product Detail Page

1. Click any product from the homepage
2. Scroll to the **recommendations section**
3. See related products with visible explanations for why they're recommended

### Step 5 – Test Recommendations API

Open PowerShell and run:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/recommendations/explainable/?query=organic&limit=3" | Select-Object -ExpandProperty Content
```

Response includes JSON with:
- Product details
- Explanation string for each recommendation
- Active model label

✅ **Part 4 complete!** Dashboard provides admin oversight; recommendations are explainable to users.

---

## Key Features

### Part 3 – AI Model Management
- ✅ Staff-only interface at `/ai/models/`
- ✅ Upload trained models as `.pkl` or `.joblib` files
- ✅ Track model version, accuracy, status (Draft/Active/Archived)
- ✅ Automatic model versioning (only one Active at a time)
- ✅ Automatic activity logging (searches, product views, cart actions)
- ✅ Export activity data as CSV for model retraining

### Part 4 – Admin Dashboard & Explainable AI
- ✅ Superuser-only dashboard at `/platform/overview/`
- ✅ Real-time platform statistics
- ✅ Activity breakdown and trend analysis
- ✅ Explainable recommendations with visible reasoning
- ✅ Model management history on admin dashboard
- ✅ Public API endpoint for recommendations: `/api/recommendations/explainable/`
- ✅ Active model label displayed with all recommendations

---

## Database & System Checks

Verify everything is working:
```powershell
python manage.py check
```

Should return: **System check identified no issues (0 silenced)**

---

## Key URLs

| URL | Purpose | Access Level |
|---|---|---|
| `/ai/models/` | Model upload & management dashboard | Staff only |
| `/ai/activity/export/` | Download activity CSV | Staff only |
| `/platform/overview/` | Admin dashboard with stats | Superuser only |
| `/api/recommendations/explainable/` | Recommendations API | Public |
| `/` | Homepage with recommendations | Public |

---

## Troubleshooting

**"Module not found" errors:**
```powershell
.venv\Scripts\pip install -r requirements.txt
```

**Database errors:**
```powershell
python manage.py migrate
```

**Server won't start:**
Ensure you're using the `.venv\Scripts\python` interpreter and the virtual environment is activated.
