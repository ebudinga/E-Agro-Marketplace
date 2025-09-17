from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Product, Order, Category

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    location = forms.CharField(max_length=100, required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'location', 'user_type', 'password1', 'password2')
        widgets = {
            'user_type': forms.RadioSelect(choices=CustomUser.USER_TYPE_CHOICES),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        self.fields['password1'].help_text = "Your password must contain at least 8 characters."
        self.fields['password2'].help_text = "Enter the same password as before, for verification."
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email
        
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number.isdigit():
            raise forms.ValidationError("Phone number should contain only digits.")
        return phone_number

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'quantity', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_method', 'delivery_address']
        widgets = {
            'delivery_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter your complete delivery address'}),
            'payment_method': forms.RadioSelect(choices=Order.PAYMENT_CHOICES)
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'payment_method':
                self.fields[field].widget.attrs.update({'class': 'form-control'})