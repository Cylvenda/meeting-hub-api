from rest_framework.routers import DefaultRouter
from .views import MeetingViewSet, AgendaItemViewSet

router = DefaultRouter()
router.register(r"meetings", MeetingViewSet, basename="meetings")
router.register(r"agenda-items", AgendaItemViewSet, basename="agenda-items")

urlpatterns = router.urls
