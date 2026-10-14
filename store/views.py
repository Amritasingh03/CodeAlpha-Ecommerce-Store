from decimal import Decimal

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Product, Order, OrderItem


def home(request):
    products = Product.objects.all()

    # Product search
    search_query = request.GET.get("q", "").strip()
    if search_query:
        products = products.filter(
            name__icontains=search_query
        ) | products.filter(
            description__icontains=search_query
        )

    # Category filter
    selected_category = request.GET.get("category", "").strip()
    if selected_category:
        products = products.filter(category=selected_category)

    categories = Product.objects.values_list(
        "category", flat=True
    ).distinct().order_by("category")

    cart = request.session.get("cart", {})
    cart_count = sum(int(qty) for qty in cart.values())

    return render(request, "home.html", {
        "products": products,
        "cart_count": cart_count,
        "categories": categories,
        "search_query": search_query,
        "selected_category": selected_category,
    })


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get("cart", {})
    key = str(product_id)
    quantity = int(cart.get(key, 0))

    if product.stock > quantity:
        cart[key] = quantity + 1

    request.session["cart"] = cart
    return redirect(request.META.get("HTTP_REFERER", "/"))


def view_cart(request):
    cart = request.session.get("cart", {})
    items = []
    total = Decimal("0.00")
    cleaned_cart = {}

    for product_id, quantity in cart.items():
        product = Product.objects.filter(id=product_id).first()

        if product is None or product.stock <= 0:
            continue

        quantity = min(max(int(quantity), 1), product.stock)
        subtotal = product.price * quantity
        total += subtotal

        items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })
        cleaned_cart[str(product.id)] = quantity

    request.session["cart"] = cleaned_cart

    return render(request, "cart.html", {
        "items": items,
        "total": total,
    })


@require_POST
def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    return redirect("view_cart")


@login_required
def checkout(request):
    cart = request.session.get("cart", {})
    items = []
    total = Decimal("0.00")

    for product_id, quantity in cart.items():
        product = Product.objects.filter(id=product_id).first()

        if product is None or product.stock <= 0:
            continue

        quantity = int(quantity)

        if quantity < 1 or quantity > product.stock:
            continue

        subtotal = product.price * quantity
        total += subtotal

        items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })

    if not items:
        return redirect("view_cart")

    if request.method == "POST":
        name = request.POST.get("customer_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()

        if not name or not phone or not address:
            return render(request, "checkout.html", {
                "items": items,
                "total": total,
                "error": "Please fill in all fields.",
            })

        if len(phone) < 7 or len(phone) > 15:
            return render(request, "checkout.html", {
                "items": items,
                "total": total,
                "error": "Please enter a valid phone number.",
            })

        with transaction.atomic():
            for item in items:
                product = Product.objects.select_for_update().get(
                    id=item["product"].id
                )

                if product.stock < item["quantity"]:
                    return render(request, "checkout.html", {
                        "items": items,
                        "total": total,
                        "error": (
                            f"Not enough stock for {product.name}. "
                            "Please return to your cart."
                        ),
                    })

            order = Order.objects.create(
                user=request.user,
                customer_name=name,
                phone=phone,
                address=address,
                total_amount=total,
            )

            for item in items:
                product = Product.objects.select_for_update().get(
                    id=item["product"].id
                )
                quantity = item["quantity"]

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                )

                product.stock -= quantity
                product.save(update_fields=["stock"])

        request.session["cart"] = {}
        return render(request, "order_success.html", {
            "order": order,
        })

    return render(request, "checkout.html", {
        "items": items,
        "total": total,
    })


@login_required
def my_orders(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by("-created_at").prefetch_related("items__product")

    return render(request, "my_orders.html", {
        "orders": orders,
    })


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"),
        pk=order_id,
        user=request.user,
    )

    return render(request, "order_detail.html", {
        "order": order,
    })


@login_required
@require_POST
def cancel_order(request, order_id):
    with transaction.atomic():
        order = get_object_or_404(
            Order.objects.select_for_update(),
            pk=order_id,
            user=request.user,
        )

        if order.status == "Placed":
            for item in order.items.select_related("product"):
                product = item.product
                product.stock += item.quantity
                product.save(update_fields=["stock"])

            order.status = "Cancelled"
            order.save(update_fields=["status"])

    return redirect("my_orders")


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()

    return render(request, "signup.html", {
        "form": form,
    })