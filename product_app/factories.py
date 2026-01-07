import factory
from django.contrib.auth.models import User
from .models import Catergory, ProductNew


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Catergory

    name = factory.Sequence(lambda n: f"Category {n}")
    description = factory.Faker("text", max_nb_chars=200)
    is_active = True


class ProductNewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductNew

    name = factory.Sequence(lambda n: f"Product {n}")
    description = factory.Faker("text", max_nb_chars=200)
    price = factory.Faker("pydecimal", left_digits=8, right_digits=2, positive=True)
    stock = factory.Faker("pyint", min_value=0, max_value=1000)
    image_url = factory.Faker("url")
    is_active = True
    category = factory.SubFactory(CategoryFactory)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True