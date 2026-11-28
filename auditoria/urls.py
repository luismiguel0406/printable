from django.urls import path

from . import views

app_name = "auditoria"
urlpatterns = [path("revisar/", views.revisar, name="revisar")]
