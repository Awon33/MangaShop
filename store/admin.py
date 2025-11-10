from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):  # <-- changed here
    list_display = ['title', 'category', 'price', 'stock', 'featured']
    list_filter = ['category', 'featured']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'author']
