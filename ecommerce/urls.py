from django.contrib import admin
from django.urls import path
from store.views import home, add_to_cart, view_cart, remove_from_cart, checkout, my_orders, order_detail, cancel_order
from django.contrib.auth import views as auth_views
from store.views import signup
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("cart/add/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path("cart/", view_cart, name="view_cart"),
    path("cart/remove/<int:product_id>/", remove_from_cart, name="remove_from_cart"),
    path("checkout/", checkout, name="checkout"),
    path("my-orders/", my_orders, name="my_orders"),
    path("my-orders/<int:order_id>/", order_detail, name="order_detail"),
    path("my-orders/<int:order_id>/cancel/", cancel_order, name="cancel_order"),
    path("signup/", signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
