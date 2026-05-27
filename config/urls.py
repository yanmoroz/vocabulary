from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from cards import api as cards_api
from cards import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("accounts/logout/", LogoutView.as_view(next_page="/accounts/login/"), name="logout"),
    path("", views.home, name="home"),
    path("review/", views.review, name="review"),
    path("rate/<int:card_id>/<int:quality>/", views.rate, name="rate"),
    path("practice/<str:direction>/", views.practice, name="practice"),
    path("practice/<str:direction>/next/", views.practice_next, name="practice_next"),
    path("practice/<str:direction>/restart/", views.practice_restart, name="practice_restart"),
    path("api/cards/", cards_api.create_card, name="api_card_create"),
]
