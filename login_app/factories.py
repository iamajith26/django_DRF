import factory
from django.contrib.auth.models import User


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating test users"""
    
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        
        password = extracted or 'testpass123'
        self.set_password(password)
        self.save()


class AdminUserFactory(UserFactory):
    """Factory for creating admin/staff users"""
    
    is_staff = True
    is_superuser = True
    username = factory.Sequence(lambda n: f"admin{n}")


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users"""
    
    is_active = False
    username = factory.Sequence(lambda n: f"inactive{n}")