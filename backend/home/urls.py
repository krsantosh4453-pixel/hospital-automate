from django.urls import path
from .views import home_dashboard, home_stats_summary

urlpatterns = [
    path("", home_dashboard, name="home-dashboard"),
    path("stats/", home_stats_summary, name="home-stats-summary"),
    path("stats/detail/", home_dashboard, name="home-stats-detail"),
]