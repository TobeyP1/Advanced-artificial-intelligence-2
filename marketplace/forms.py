from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from .models import AIModel, CustomerProfile, ProducerProfile, Product


class CustomerRegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    delivery_address = forms.CharField(widget=forms.Textarea)
    postcode = forms.CharField(max_length=20)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    accept_terms = forms.BooleanField()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        if p1:
            validate_password(p1)
        return cleaned

    def save(self):
        email = self.cleaned_data["email"].strip().lower()
        password = self.cleaned_data["password1"]

        user = User.objects.create_user(username=email, email=email, password=password)

        CustomerProfile.objects.create(
            user=user,
            full_name=self.cleaned_data["full_name"],
            phone=self.cleaned_data["phone"],
            delivery_address=self.cleaned_data["delivery_address"],
            postcode=self.cleaned_data["postcode"],
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
        )
        return user


class ProducerRegistrationForm(forms.Form):
    producer_name = forms.CharField(max_length=200)
    contact_name = forms.CharField(max_length=200)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    address = forms.CharField(widget=forms.Textarea)
    postcode = forms.CharField(max_length=20)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        if p1:
            validate_password(p1)

        return cleaned

    def save(self):
        email = self.cleaned_data["email"].strip().lower()
        password = self.cleaned_data["password1"]

        user = User.objects.create_user(username=email, email=email, password=password)

        ProducerProfile.objects.create(
            user=user,
            producer_name=self.cleaned_data["producer_name"],
            contact_name=self.cleaned_data["contact_name"],
            phone=self.cleaned_data["phone"],
            address=self.cleaned_data["address"],
            postcode=self.cleaned_data["postcode"],
        )
        return user


class ProducerProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "price",
            "category",
            "description",
            "allergen_info",
            "organic_certified",
            "harvest_date",
            "stock_quantity",
            "availability_status",
        ]

    def clean_stock_quantity(self):
        stock_quantity = self.cleaned_data.get("stock_quantity", 0)
        if stock_quantity < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return stock_quantity

    def clean_allergen_info(self):
        allergen_info = self.cleaned_data.get("allergen_info", "").strip()
        if not allergen_info:
            raise forms.ValidationError(
                "Allergen information is required. Use 'None' if no common allergens."
            )
        return allergen_info


class AIModelUploadForm(forms.ModelForm):
    class Meta:
        model = AIModel
        fields = ["name", "version", "description", "model_file", "accuracy_score", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_version(self):
        return self.cleaned_data["version"].strip()
