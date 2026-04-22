from django.core.management.base import BaseCommand

from marketplace.models import Category


class Command(BaseCommand):
    help = "Create default marketplace categories if they do not exist"

    DEFAULT_CATEGORIES = [
        ("Vegetables", "vegetables"),
        ("Fruit", "fruit"),
        ("Dairy & Eggs", "dairy-eggs"),
        ("Bakery", "bakery"),
        ("Meat", "meat"),
        ("Fish", "fish"),
        ("Pantry", "pantry"),
    ]

    def handle(self, *args, **options):
        created = 0

        for name, slug in self.DEFAULT_CATEGORIES:
            _, was_created = Category.objects.get_or_create(slug=slug, defaults={"name": name})
            if was_created:
                created += 1

        if created == 0:
            self.stdout.write(self.style.WARNING("No new categories created (all already exist)."))
            return

        self.stdout.write(self.style.SUCCESS(f"Created {created} categories."))
