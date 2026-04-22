from decimal import Decimal

from .models import Product


class Cart:
    SESSION_KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(self.SESSION_KEY)
        if cart is None:
            cart = {}
            self.session[self.SESSION_KEY] = cart
        self.cart = cart

    def save(self):
        self.session.modified = True

    def _normalize_quantity(self, quantity):
        quantity_value = int(quantity)
        if quantity_value < 1:
            return 1
        return quantity_value

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        quantity_value = self._normalize_quantity(quantity)

        if product_id not in self.cart:
            self.cart[product_id] = {"quantity": 0, "price": str(product.price)}

        if override_quantity:
            self.cart[product_id]["quantity"] = quantity_value
        else:
            self.cart[product_id]["quantity"] += quantity_value

        self.save()

    def add_product(self, product, quantity=1):
        self.add(product, quantity=quantity, override_quantity=False)

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def remove_product(self, product_id):
        product_id_str = str(product_id)
        if product_id_str in self.cart:
            del self.cart[product_id_str]
            self.save()

    def update_quantity(self, product_id, quantity):
        product_id_str = str(product_id)
        if product_id_str not in self.cart:
            return

        quantity_value = int(quantity)
        if quantity_value <= 0:
            del self.cart[product_id_str]
        else:
            self.cart[product_id_str]["quantity"] = quantity_value
        self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)

        cart_copy = self.cart.copy()
        for product in products:
            cart_copy[str(product.id)]["product"] = product

        for item in cart_copy.values():
            item["price"] = Decimal(item["price"])
            item["total_price"] = item["price"] * item["quantity"]
            yield item

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    def get_total_items(self):
        return len(self)

    def get_total_price(self):
        return sum(Decimal(item["price"]) * item["quantity"] for item in self.cart.values())

    def clear(self):
        self.session.pop(self.SESSION_KEY, None)
        self.save()

    def clear_cart(self):
        self.clear()