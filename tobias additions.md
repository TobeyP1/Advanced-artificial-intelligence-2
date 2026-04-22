# Tobias Additions

## Brief rundown of changes

Implemented around test cases **TC-001**, **TC-003**, and **TC-006**.

- Added producer web registration flow:
  - `register/producer/` route
  - `ProducerRegistrationForm` in `marketplace/forms.py`
  - `register_producer` view in `marketplace/views.py`
  - `marketplace/templates/marketplace/register_producer.html`
- Added producer product management flow:
  - `producer/products/` dashboard route
  - `producer/products/new/` create-product route
  - `ProducerProductForm` in `marketplace/forms.py`
  - `producer_products` and `producer_product_create` views in `marketplace/views.py`
  - `producer_products.html` and `producer_product_form.html` templates
- Added category bootstrap support:
  - `seed_categories` management command in `marketplace/management/commands/seed_categories.py`
  - producer product create view now warns/redirects if categories are missing
- Added customer cart flow (TC-006 support):
  - session-based cart utility in `marketplace/cart.py`
  - product/cart routes in `marketplace/urls.py`
  - cart/product views in `marketplace/views.py`
  - new templates: `cart.html`, `product_detail.html`
  - updated `home.html` and `category.html` for cart links and add-to-cart actions

## Demo run/test steps

### 1) Start app with Docker
```powershell
Set-Location "c:\Users\Tobey\Desktop\DESD\DESD-1"
docker compose up -d --build
```

### 2) Seed categories (needed for producer product form)
```powershell
docker compose exec web python manage.py seed_categories
```

### 3) (One-time) Create admin user (optional but useful)
```powershell
docker compose exec web python manage.py createsuperuser
```

### 4) TC-001 demo: Producer registration
1. Open `http://localhost:8000/register/producer/`
2. Fill in producer details and submit.
3. Log in at `http://localhost:8000/accounts/login/`.

### 5) TC-003 demo: Producer adds a product
1. Open `http://localhost:8000/producer/products/`.
2. Click **Add New Product**.
3. Fill product details (name, category, price, stock, availability) and save.
4. Confirm product appears in producer list and category browsing.

### 6) TC-006 demo: Customer cart behavior
1. Open `http://localhost:8000/` and browse/search products.
2. Open a product and add quantity to cart.
3. Add a second product.
4. Open `http://localhost:8000/cart/`.
5. Verify both products, quantities, and total.
6. Update one quantity and verify total recalculates.

### 7) Basic check
```powershell
docker compose exec web python manage.py check
```

## Additional changes for TC-011, TC-014 and TC-015

- Added producer product editing for **TC-011**:
  - `producer/products/<int:pk>/edit/` route
  - `producer_product_update` view in `marketplace/views.py`
  - edit links added in `marketplace/templates/marketplace/producer_products.html`
  - stock quantity validation added in `ProducerProductForm` so values cannot be negative
- Added organic certification support for **TC-014**:
  - `organic_certified` field added to `Product` model in `marketplace/models.py`
  - migration added: `marketplace/migrations/0002_product_organic_certified.py`
  - organic checkbox added to producer product form
  - organic status shown in producer dashboard, product detail, and customer browse/search pages
  - organic filters added to `home.html` and `category.html`
- Added allergen warnings support for **TC-015**:
  - allergen information is now required in producer product form (use `None` if no common allergens)
  - allergen warnings shown on product detail page and category/search results
  - allergen filter added to product browsing/search

## Demo steps for TC-011, TC-014 and TC-015

### 8) TC-011 demo: Producer updates inventory
1. Log in as a producer.
2. Open `http://localhost:8000/producer/products/`.
3. Click **Edit** on an existing product.
4. Change stock quantity and/or availability status.
5. Save and confirm the updated values appear in the producer dashboard.

### 9) TC-014 demo: Organic certification filter
1. Open a producer product form and tick **organic certified** for at least one product.
2. Open `http://localhost:8000/` or a category page.
3. Use the **Organic** filter and choose **Certified Organic**.
4. Confirm only organic-certified products are shown.
5. Open a product detail page and confirm the organic status is displayed.

### 10) TC-015 demo: Allergen warnings
1. Open a product with allergen info recorded.
2. Confirm the product detail page shows **Contains:** followed by allergens.
3. Open a product with `None` or no common allergens and confirm that message is shown clearly.
4. Use the allergen filter on the home/category page (for example `milk` or `nuts`).
5. Confirm only matching products are returned.

## Case study parts 3 and 4

A non-functional project write-up has also been added for the remaining case study requirements:
- **Part 3:** AI engineer access for model retraining, model upload, and interaction-data usage.
- **Part 4:** main administrator visibility plus explainable AI requirements.

This was added as documentation only so the group project can reference those requirements without introducing extra implementation work.
