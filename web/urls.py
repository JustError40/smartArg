from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("chats/", views.chat_list, name="chat_list"),
    path("knowledge-base/", views.knowledge_base, name="knowledge_base"),
]
