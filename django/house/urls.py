from django.conf.urls import url, patterns

from . import views

urlpatterns = patterns("house.views",
    url(r'^api$', views.api_view, name='api'),
    url(r'^$', views.index_view, name='index'),
)
