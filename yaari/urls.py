"""
URL configuration for yaari project.

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
from django.urls import path
from resolver.views import yaari_assoc_req
from resolver.views import yaari_assoc
from resolver.views import yaari_de_assoc
from resolver.views import yaari_assoc_chat_id
from resolver.views import yaari_notify
from resolver.views import yaari_hoax_auditor
from resolver.views import yaari_action_notify
from resolver.views import yaari_two_step_verification

urlpatterns = [
    path('admin/', admin.site.urls),
    path('assoc_req/', yaari_assoc_req, name="yaari_assoc_req"),
    path('assoc/', yaari_assoc, name="yaari_assoc"),
    path('de_assoc/', yaari_de_assoc, name="yaari_de_assoc"),
    path('assoc_chat_id/', yaari_assoc_chat_id, name="yaari_assoc_chat_id"),
    path('yaari_notify/', yaari_notify, name="yaari_notify"),
    path('yaari_hoax_auditor/', yaari_hoax_auditor, name="yaari_hoax_auditor"),
    path('yaari_action_notify/', yaari_action_notify, name="yaari_action_notify"),
    path('yaari_two_step_verification/, yaari_two_step_verification, name="yaari_two_step_verification") 
]
