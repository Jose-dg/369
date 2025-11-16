from django.urls import path
from .views import RetryEventView

urlpatterns = [
    path('retry/<uuid:event_id>/', RetryEventView.as_view(), name='retry-event'),
]
