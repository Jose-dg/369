from django.urls import path
from .views import RegisterUniqueCodesView

urlpatterns = [
    path('unique-codes/register/', RegisterUniqueCodesView.as_view(), name='register-unique-codes'),
]
