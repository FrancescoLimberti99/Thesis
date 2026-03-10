from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('artworks/', views.artwork_list, name='artwork_list'),
    path('artworks/<int:pk>/', views.artwork_detail, name='artwork_detail'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]