from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from cart.models import Cart
from .forms import UserUpdateForm, ProfileUpdateForm

def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('store:product_list')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # TRANSFER SESSION CART TO USER CART
                from cart.views import transfer_session_cart_to_user
                transfer_session_cart_to_user(request, user)
                
                messages.success(request, f"Welcome back, {username}!")
                
                # Redirect to next page or cart
                next_url = request.session.get('next_url', 'store:product_list')
                if 'next_url' in request.session:
                    del request.session['next_url']
                return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('store:product_list')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Create user profile - this will automatically set created_at
                UserProfile.objects.create(user=user)
                
                # Create cart for user
                Cart.objects.create(user=user)
                
                # Login user
                login(request, user)
                messages.success(request, f"Account created for {user.username}!")
                return redirect('store:product_list')
                
            except Exception as e:
                messages.error(request, f"Error creating profile: {str(e)}")
                return render(request, 'accounts/register.html', {'form': form})
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('store:product_list')

@login_required
def profile_view(request):
    """User profile view"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update user info
        request.user.email = request.POST.get('email', '')
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        
        # Update profile info
        profile.phone = request.POST.get('phone', '')
        profile.address = request.POST.get('address', '')
        profile.city = request.POST.get('city', '')
        profile.state = request.POST.get('state', '')
        profile.postal_code = request.POST.get('postal_code', '')
        profile.country = request.POST.get('country', '')
        profile.save()
        
        messages.success(request, 'Your profile has been updated!')
        return redirect('accounts:profile')
    
    context = {
        'profile': profile,
    }
    return render(request, 'accounts/profile.html', context)