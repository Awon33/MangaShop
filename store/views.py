from django.shortcuts import render, get_object_or_404
from .models import Product, Category

def home(request):
    featured_products = Product.objects.filter(featured=True)[:4]
    return render(request, 'store/home.html', {
        'featured_products': featured_products
    })

def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    
    # Filter by category if provided
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {
        'product': product
    })

def category_detail(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category)
    return render(request, 'store/category_detail.html', {
        'category': category,
        'products': products
    })