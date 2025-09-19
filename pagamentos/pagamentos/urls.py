"""
URL configuration for pagamentos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

# Personalizando os títulos do painel de administração
admin.site.site_header = "Administração API Pagamentos"
admin.site.site_title = "Painel Administrativo"
admin.site.index_title = "Bem-vindo à Administração da API de Pagamentos"


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('mpesa_app.urls')),
]
