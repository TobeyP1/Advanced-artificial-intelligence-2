from django import forms

# Keep parity with the source Flask app extension allowlist.
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}


class FreshnessUploadForm(forms.Form):
    image = forms.ImageField(required=True)
    product_type = forms.CharField(max_length=40, required=False)

    def clean_image(self):
        image = self.cleaned_data["image"]
        name = (image.name or "").lower()
        if "." not in name:
            raise forms.ValidationError("Invalid file type. Use PNG, JPG, JPEG, WEBP, or BMP.")

        ext = name.rsplit(".", 1)[1]
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Invalid file type. Use PNG, JPG, JPEG, WEBP, or BMP.")

        return image
