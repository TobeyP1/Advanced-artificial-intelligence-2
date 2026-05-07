from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import AIModel, Category, Product, ProducerProfile, UserActivityLog

User = get_user_model()


class MarketplaceCoreTests(TestCase):
    def setUp(self):
        self.producer_user = User.objects.create_user(
            username="producer@example.com",
            email="producer@example.com",
            password="StrongPass123!",
        )
        self.producer_profile = ProducerProfile.objects.create(
            user=self.producer_user,
            producer_name="Green Farm",
            contact_name="Green Farm",
            phone="0123456789",
            address="1 High Street",
            postcode="BS1 1AA",
        )
        self.category = Category.objects.create(name="Fruit", slug="fruit")
        self.product = Product.objects.create(
            name="Apple",
            price="1.20",
            category=self.category,
            producer=self.producer_profile,
            description="Local apples",
            allergen_info="None",
            stock_quantity=8,
            availability_status=Product.AVAILABLE,
        )

    def test_home_page_renders(self):
        response = self.client.get(reverse("marketplace:home"))
        self.assertEqual(response.status_code, 200)

    def test_explainable_recommendations_api_returns_payload(self):
        response = self.client.get(reverse("marketplace:explainable_recommendations"))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("active_model", body)
        self.assertIn("recommendations", body)

    def test_cart_add_logs_user_activity(self):
        response = self.client.post(
            reverse("marketplace:add_to_cart", args=[self.product.id]),
            {"quantity": 2},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            UserActivityLog.objects.filter(action=UserActivityLog.CART_ADD, product=self.product).exists()
        )

    def test_new_active_model_archives_previous_active_model(self):
        first_model = AIModel.objects.create(
            name="recommender",
            version="1.0",
            model_file=SimpleUploadedFile("model-v1.joblib", b"model-v1"),
            status=AIModel.ACTIVE,
        )

        second_model = AIModel.objects.create(
            name="recommender",
            version="1.1",
            model_file=SimpleUploadedFile("model-v2.joblib", b"model-v2"),
            status=AIModel.ACTIVE,
        )

        first_model.refresh_from_db()
        second_model.refresh_from_db()

        self.assertEqual(first_model.status, AIModel.ARCHIVED)
        self.assertEqual(second_model.status, AIModel.ACTIVE)
