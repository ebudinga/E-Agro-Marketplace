from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Product, Order, Category, FarmerSubaccount


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    location = forms.CharField(max_length=100, required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'location',
                  'user_type', 'password1', 'password2')
        widgets = {
            'user_type': forms.RadioSelect(choices=CustomUser.USER_TYPE_CHOICES),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = "150 chars max. Letters, digits and @/./+/-/_."
        self.fields['password1'].help_text = "At least 8 characters."
        self.fields['password2'].help_text = "Repeat your password."
        for f in self.fields.values():
            f.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        if not phone.isdigit():
            raise forms.ValidationError("Phone number should contain only digits.")
        return phone


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'quantity', 'category', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_method', 'delivery_address']
        widgets = {
            'delivery_address': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Enter your complete delivery address including landmarks',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].choices = Order.PAYMENT_CHOICES
        self.fields['payment_method'].empty_label = None


class FarmerBankForm(forms.ModelForm):
    """Used to create / update a farmer's Paystack subaccount."""
    bank_code = forms.ChoiceField(choices=[], required=True)
    account_number = forms.CharField(max_length=10, required=True, min_length=10)

    class Meta:
        model = FarmerSubaccount
        fields = ['business_name', 'account_number']

    def __init__(self, *args, bank_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_code'].choices = [('', 'Select your bank')] + (bank_choices or [])
        self.fields['business_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['account_number'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '10-digit NUBAN account number',
            'maxlength': '10',
        })
        self.fields['bank_code'].widget.attrs.update({'class': 'form-select'})