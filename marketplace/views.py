import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .cart import Cart
from .forms import (
    AIModelUploadForm,
    CustomerRegistrationForm,
    ProducerProductForm,
    ProducerRegistrationForm,
)
from .models import AIModel, Category, CustomerProfile, Product, ProducerProfile, UserActivityLog
from .serializers import ProducerRegistrationSerializer, ProductSerializer

User = get_user_model()


def _is_staff_user(user):
    return user.is_authenticated and user.is_staff


def _is_superuser(user):
    return user.is_authenticated and user.is_superuser


def _get_active_model_info():
    active_model = AIModel.objects.filter(status=AIModel.ACTIVE).first()
    if active_model:
        return active_model, f"{active_model.name} v{active_model.version}"
    return None, "Rule-based recommender v1"


def _log_activity(request, action, product=None, search_query="", details=None):
    if not request.session.session_key:
        request.session.save()

    UserActivityLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or "",
        action=action,
        product=product,
        search_query=search_query[:200],
        details=details or {},
    )


def _remember_product_view(request, product_id):
    recent_ids = request.session.get("recently_viewed_products", [])
    recent_ids = [pid for pid in recent_ids if pid != product_id]
    recent_ids.insert(0, product_id)
    request.session["recently_viewed_products"] = recent_ids[:10]


def _get_explainable_recommendations(request, current_product=None, limit=4):
    products = Product.objects.select_related("category", "producer").filter(
        availability_status__in=[Product.AVAILABLE, Product.IN_SEASON],
        stock_quantity__gt=0,
    )

    if current_product:
        products = products.exclude(pk=current_product.pk)

    recent_ids = request.session.get("recently_viewed_products", [])
    recent_categories = set(Product.objects.filter(pk__in=recent_ids).values_list("category_id", flat=True))
    search_query = request.GET.get("q", "").strip().lower()

    if current_product:
        recent_categories.add(current_product.category_id)

    prioritized = products
    if recent_categories:
        prioritized = products.filter(category_id__in=recent_categories)

    recommendations = []
    used_ids = set()

    for candidate in list(prioritized[: limit * 3]) + list(products[: limit * 3]):
        if candidate.id in used_ids:
            continue

        reasons = []
        searchable_text = " ".join(
            [candidate.name or "", candidate.description or "", candidate.producer.producer_name or ""]
        ).lower()

        if current_product and candidate.category_id == current_product.category_id:
            reasons.append(f"same category as {current_product.name}")
        elif candidate.category_id in recent_categories:
            reasons.append("matches categories viewed recently")

        if search_query and search_query in searchable_text:
            reasons.append("matches your recent search")

        if candidate.organic_certified:
            reasons.append("organic certified")

        if candidate.availability_status == Product.IN_SEASON:
            reasons.append("currently in season")

        reasons.append("available in stock now")

        recommendations.append(
            {
                "product": candidate,
                "explanation": "; ".join(reasons[:3]).capitalize() + ".",
            }
        )
        used_ids.add(candidate.id)

        if len(recommendations) >= limit:
            break

    return recommendations


def home(request):
    cart = Cart(request)
    categories = Category.objects.all()
    query = request.GET.get("q", "").strip()
    organic_filter = request.GET.get("organic", "").strip()
    allergen_filter = request.GET.get("allergen", "").strip()

    search_performed = bool(query or organic_filter or allergen_filter)
    products = Product.objects.none()

    if search_performed:
        products = Product.objects.select_related("producer", "category").filter(
            availability_status__in=[Product.AVAILABLE, Product.IN_SEASON],
        )

        if query:
            products = products.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(producer__producer_name__icontains=query)
            )

        if organic_filter == "certified":
            products = products.filter(organic_certified=True)
        elif organic_filter == "not_certified":
            products = products.filter(organic_certified=False)

        if allergen_filter:
            products = products.filter(allergen_info__icontains=allergen_filter)

        products = products.distinct()
        _log_activity(
            request,
            UserActivityLog.SEARCH,
            search_query=query,
            details={"organic": organic_filter, "allergen": allergen_filter},
        )

    active_model, active_model_label = _get_active_model_info()

    context = {
        "categories": categories,
        "search_query": query,
        "organic_filter": organic_filter,
        "allergen_filter": allergen_filter,
        "search_results": products,
        "search_performed": search_performed,
        "cart_total_items": cart.get_total_items(),
        "recommendations": _get_explainable_recommendations(request, limit=4),
        "active_ai_model": active_model,
        "active_ai_model_label": active_model_label,
    }
    return render(request, "marketplace/home.html", context)


def register_customer(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
    else:
        form = CustomerRegistrationForm()

    return render(request, "marketplace/register.html", {"form": form})


def register_producer(request):
    if request.method == "POST":
        form = ProducerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Producer account created. Please log in.")
            return redirect("login")
    else:
        form = ProducerRegistrationForm()

    return render(request, "marketplace/register_producer.html", {"form": form})


@login_required
def producer_products(request):
    try:
        producer = ProducerProfile.objects.get(user=request.user)
    except ProducerProfile.DoesNotExist:
        messages.error(request, "You do not have a producer profile yet.")
        return redirect("marketplace:register_producer")

    products = Product.objects.filter(producer=producer).select_related("category")
    return render(
        request,
        "marketplace/producer_products.html",
        {"producer": producer, "products": products},
    )


@login_required
def producer_product_create(request):
    try:
        producer = ProducerProfile.objects.get(user=request.user)
    except ProducerProfile.DoesNotExist:
        messages.error(request, "You do not have a producer profile yet.")
        return redirect("marketplace:register_producer")

    if not Category.objects.exists():
        messages.error(request, "No categories exist yet. Ask an admin to add categories first.")
        return redirect("marketplace:producer_products")

    if request.method == "POST":
        form = ProducerProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = producer
            product.save()
            messages.success(request, "Product listed successfully.")
            return redirect("marketplace:producer_products")
    else:
        form = ProducerProductForm()

    return render(
        request,
        "marketplace/producer_product_form.html",
        {"form": form, "form_mode": "create"},
    )


@login_required
def producer_product_update(request, pk):
    try:
        producer = ProducerProfile.objects.get(user=request.user)
    except ProducerProfile.DoesNotExist:
        messages.error(request, "You do not have a producer profile yet.")
        return redirect("marketplace:register_producer")

    product = get_object_or_404(Product, pk=pk, producer=producer)

    if request.method == "POST":
        form = ProducerProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully.")
            return redirect("marketplace:producer_products")
    else:
        form = ProducerProductForm(instance=product)

    return render(
        request,
        "marketplace/producer_product_form.html",
        {"form": form, "form_mode": "edit", "product": product},
    )


def category_products(request, slug):
    cart = Cart(request)
    category = get_object_or_404(Category, slug=slug)
    organic_filter = request.GET.get("organic", "").strip()
    allergen_filter = request.GET.get("allergen", "").strip()

    products = Product.objects.filter(
        category=category,
        availability_status__in=[Product.AVAILABLE, Product.IN_SEASON],
    )

    if organic_filter == "certified":
        products = products.filter(organic_certified=True)
    elif organic_filter == "not_certified":
        products = products.filter(organic_certified=False)

    if allergen_filter:
        products = products.filter(allergen_info__icontains=allergen_filter)

    return render(
        request,
        "marketplace/category.html",
        {
            "category": category,
            "products": products,
            "organic_filter": organic_filter,
            "allergen_filter": allergen_filter,
            "cart_total_items": cart.get_total_items(),
        },
    )


def product_detail(request, pk):
    cart = Cart(request)
    product = get_object_or_404(
        Product,
        pk=pk,
        availability_status__in=[Product.AVAILABLE, Product.IN_SEASON],
    )

    _remember_product_view(request, product.id)
    _log_activity(
        request,
        UserActivityLog.PRODUCT_VIEW,
        product=product,
        details={"category": product.category.name, "producer": product.producer.producer_name},
    )

    active_model, active_model_label = _get_active_model_info()

    return render(
        request,
        "marketplace/product_detail.html",
        {
            "product": product,
            "cart_total_items": cart.get_total_items(),
            "recommendations": _get_explainable_recommendations(request, current_product=product, limit=4),
            "active_ai_model": active_model,
            "active_ai_model_label": active_model_label,
        },
    )


def cart_detail(request):
    cart = Cart(request)
    return render(
        request,
        "marketplace/cart.html",
        {"cart": cart, "cart_total_items": cart.get_total_items()},
    )


@require_POST
def add_to_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)

    quantity_raw = request.POST.get("quantity", "1")
    try:
        quantity = int(quantity_raw)
    except (TypeError, ValueError):
        quantity = 1

    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("marketplace:product_detail", pk=product.id)

    if product.availability_status not in [Product.AVAILABLE, Product.IN_SEASON]:
        messages.error(request, "This product is currently unavailable.")
        return redirect("marketplace:product_detail", pk=product.id)

    if product.stock_quantity <= 0:
        messages.error(request, "This product is out of stock.")
        return redirect("marketplace:product_detail", pk=product.id)

    if quantity > product.stock_quantity:
        quantity = product.stock_quantity
        messages.warning(
            request,
            f"Only {product.stock_quantity} in stock. Added available quantity.",
        )

    cart.add(product=product, quantity=quantity)
    _log_activity(request, UserActivityLog.CART_ADD, product=product, details={"quantity": quantity})
    messages.success(request, f"Added {quantity} × {product.name} to cart.")

    next_url = request.POST.get("next", "").strip()
    if next_url:
        return redirect(next_url)

    return redirect("marketplace:cart_detail")


@require_POST
def update_cart_item(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)

    quantity_raw = request.POST.get("quantity", "1")
    try:
        quantity = int(quantity_raw)
    except (TypeError, ValueError):
        quantity = 1

    if quantity <= 0:
        cart.remove(product)
        _log_activity(request, UserActivityLog.CART_REMOVE, product=product, details={"quantity": 0})
        messages.success(request, f"Removed {product.name} from cart.")
    else:
        if quantity > product.stock_quantity:
            quantity = product.stock_quantity
            messages.warning(
                request,
                f"Only {product.stock_quantity} in stock. Quantity adjusted.",
            )
        cart.add(product=product, quantity=quantity, override_quantity=True)
        _log_activity(request, UserActivityLog.CART_UPDATE, product=product, details={"quantity": quantity})
        messages.success(request, f"Updated {product.name} quantity to {quantity}.")

    return redirect("marketplace:cart_detail")


@require_POST
def remove_from_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id)
    cart.remove(product)
    _log_activity(request, UserActivityLog.CART_REMOVE, product=product, details={"quantity": 0})
    messages.success(request, f"Removed {product.name} from cart.")
    return redirect("marketplace:cart_detail")


@user_passes_test(_is_staff_user, login_url="/accounts/login/")
def ai_model_dashboard(request):
    if request.method == "POST":
        form = AIModelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            model = form.save(commit=False)
            model.uploaded_by = request.user
            model.save()
            _log_activity(
                request,
                UserActivityLog.MODEL_UPLOAD,
                details={"model_name": model.name, "version": model.version, "status": model.status},
            )
            messages.success(request, "AI model uploaded successfully.")
            return redirect("marketplace:ai_model_dashboard")
    else:
        form = AIModelUploadForm()

    models = AIModel.objects.select_related("uploaded_by").all()
    active_model, active_model_label = _get_active_model_info()
    return render(
        request,
        "marketplace/ai_model_dashboard.html",
        {
            "form": form,
            "models": models,
            "active_ai_model": active_model,
            "active_ai_model_label": active_model_label,
        },
    )


@user_passes_test(_is_staff_user, login_url="/accounts/login/")
def export_activity_data(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="user_activity_export.csv"'

    writer = csv.writer(response)
    writer.writerow(["timestamp", "user", "session_key", "action", "product", "search_query", "details"])

    logs = UserActivityLog.objects.select_related("user", "product").all().order_by("-created_at")
    for log in logs:
        writer.writerow(
            [
                log.created_at.isoformat(),
                log.user.username if log.user else "anonymous",
                log.session_key,
                log.action,
                log.product.name if log.product else "",
                log.search_query,
                log.details,
            ]
        )

    return response


@user_passes_test(_is_superuser, login_url="/accounts/login/")
def admin_dashboard(request):
    seven_days_ago = timezone.now() - timedelta(days=7)
    active_model, active_model_label = _get_active_model_info()

    context = {
        "stats": {
            "total_users": User.objects.count(),
            "customer_profiles": CustomerProfile.objects.count(),
            "producer_profiles": ProducerProfile.objects.count(),
            "total_products": Product.objects.count(),
            "available_products": Product.objects.filter(
                availability_status__in=[Product.AVAILABLE, Product.IN_SEASON]
            ).count(),
            "low_stock_products": Product.objects.filter(stock_quantity__lte=5).count(),
            "activity_last_7_days": UserActivityLog.objects.filter(created_at__gte=seven_days_ago).count(),
        },
        "recent_activity": UserActivityLog.objects.select_related("user", "product")[:20],
        "activity_breakdown": UserActivityLog.objects.values("action").annotate(total=Count("id")).order_by("-total"),
        "top_searches": UserActivityLog.objects.filter(action=UserActivityLog.SEARCH)
        .exclude(search_query="")
        .values("search_query")
        .annotate(total=Count("id"))
        .order_by("-total")[:5],
        "models": AIModel.objects.select_related("uploaded_by")[:5],
        "recommendations": _get_explainable_recommendations(request, limit=5),
        "active_ai_model": active_model,
        "active_ai_model_label": active_model_label,
    }
    return render(request, "marketplace/admin_dashboard.html", context)


class ProducerRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = ProducerRegistrationSerializer
    permission_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"detail": "Producer account created successfully. Please log in."},
            status=status.HTTP_201_CREATED,
        )


class ExplainableRecommendationsView(generics.GenericAPIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        product_id = request.GET.get("product_id")
        current_product = Product.objects.filter(pk=product_id).first() if product_id else None
        _, active_model_label = _get_active_model_info()

        recommendations = _get_explainable_recommendations(request, current_product=current_product, limit=5)
        return Response(
            {
                "active_model": active_model_label,
                "recommendations": [
                    {
                        "product_id": item["product"].id,
                        "name": item["product"].name,
                        "price": str(item["product"].price),
                        "producer": item["product"].producer.producer_name,
                        "explanation": item["explanation"],
                    }
                    for item in recommendations
                ],
            }
        )


class ProducerProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        producer = get_object_or_404(ProducerProfile, user=self.request.user)
        return Product.objects.filter(producer=producer)

    def perform_create(self, serializer):
        producer = get_object_or_404(ProducerProfile, user=self.request.user)
        serializer.save(producer=producer)


class ProducerProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        producer = get_object_or_404(ProducerProfile, user=self.request.user)
        return Product.objects.filter(producer=producer)
