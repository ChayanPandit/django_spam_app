from django.urls import path
from .views import RegisterView, LoginView, GetUsersView
from .views import RegisterView, ContactListCreateView, SearchByNameView, SearchByPhoneNumberView, GlobalView, GetUserDetailView, MarkSpamView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('contacts/', ContactListCreateView.as_view(), name='contacts'),
    path('search/name/', SearchByNameView.as_view(), name='search-by-name'),
    path('search/phone/', SearchByPhoneNumberView.as_view(), name='search-by-phone'),
    path('getusers/', GetUsersView.as_view(), name='getusers'),
    path('login/', LoginView.as_view(), name='login'),
    path('global/', GlobalView.as_view(), name='global'),
    path('user/', GetUserDetailView.as_view(), name='user'),
    path('markspam/', MarkSpamView.as_view(), name='markspam'),

]
