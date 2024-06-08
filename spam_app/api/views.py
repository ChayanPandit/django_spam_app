from django.http import Http404, JsonResponse
from rest_framework import generics, permissions, views, response
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate, login, logout
from .models import Contact
from .serializers import UserSerializer, ContactSerializer, GlobalSerializer
# from knox.models import AuthToken
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
import jwt
from dotenv import load_dotenv
import os
load_dotenv()
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db.models import Case, When, Value, IntegerField
from django.db.models import F, ExpressionWrapper, FloatField, Sum, Q, Count
from django.db.models.functions import RowNumber
from django.db.models import Window
from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.db.models import Subquery, OuterRef, Count

from django.db.models.functions import Coalesce

JWT_SECRET=os.getenv("JWT_SECRET")
User = get_user_model()

    

def get_global_database():
    
        user_queryset = User.objects.all()
        
        user_phone_numbers = user_queryset.values_list('phone_number', flat=True)
        
        user_queryset = user_queryset.annotate(
            spam_likelihood=ExpressionWrapper(
                F('spam_of') / Coalesce(F('contact_of'), 1),
                output_field=FloatField()
            ),
            is_user=Value(True, output_field=models.BooleanField())
        ).values('id', 'name', 'phone_number', 'spam_likelihood', 'is_user', 'spam_of', 'contact_of')
        
        
        contact_queryset = Contact.objects.exclude(
            phone_number__in=user_phone_numbers
            ).annotate(
            is_user=Value(False, output_field=models.BooleanField()),
            contact_of=Coalesce(
                Subquery(
                    Contact.objects.filter(phone_number=OuterRef('phone_number'))
                    .values('phone_number')
                    .annotate(count=Count('id'))
                    .values('count')[:1]
                ),
                0
            ),
            spam_of=Coalesce(
                Subquery(
                    Contact.objects.filter(phone_number=OuterRef('phone_number'))
                    .values('phone_number')
                    .filter(is_spam=True)
                    .annotate(count=Count('id'))
                    .values('count')[:1]
                ),
                0
            ),
            spam_likelihood=ExpressionWrapper(
                F('spam_of') * 100.0 / Coalesce(F('contact_of'), 1),
                output_field=FloatField()
            )
        ).values('id', 'name', 'phone_number', 'spam_likelihood', 'is_user', 'spam_of', 'contact_of')


        return user_queryset, contact_queryset
 
    
    
class GetUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        content = {
            'user': str(request.user),  
            'auth': str(request.auth), 
        }
        return Response(content)

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
class LoginView(APIView):
    authentication_classes = [TokenAuthentication]
    def post(self, request):
        phone_number=request.data['phone_number']    
        password=request.data['password']
        
        user = authenticate(phone_number=phone_number, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key})
        else:
            return Response({'error': 'Invalid login credentials'})

class ContactListCreateView(generics.ListCreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SearchByNameView(generics.ListAPIView):
    serializer_class = GlobalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('name', '')
        
        user_queryset, contact_queryset = get_global_database()
          
        if query:
            user_queryset = user_queryset.annotate(
                starts_with_query=Case(
                    When(name__istartswith=query, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).filter(name__icontains=query).order_by('starts_with_query', 'name')
            
            user_queryset = user_queryset.filter(name__istartswith=query)
                
        if query:
            contact_queryset = contact_queryset.annotate(
                starts_with_query=Case(
                    When(name__istartswith=query, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).filter(name__icontains=query).order_by('starts_with_query', 'name')
        
        queryset = list(user_queryset) + list(contact_queryset)
        queryset.sort(key=lambda x: (x['starts_with_query'], x['name']))

        return queryset

class SearchByPhoneNumberView(generics.ListAPIView):
    serializer_class = GlobalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('phone', '')

        user_queryset, contact_queryset = get_global_database()

        user_queryset = user_queryset.filter(phone_number=query)
        
        if user_queryset.count()>0:
            return user_queryset
        
        contact_queryset = contact_queryset.filter(phone_number=query)
        return contact_queryset

class GetUserDetailView(generics.RetrieveAPIView):
    serializer_class =  UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        query = self.request.query_params.get('id', '')
        user_queryset = User.objects.filter(id=query)
        if user_queryset.exists():
            user = user_queryset.first()
            self.serializer_class.Meta.fields += ['email', 'spam_likelihood']
            return user
        
        contact_queryset  = Contact.objects.filter(id=query)

        contact = contact_queryset.first()
        if contact_queryset.exists():
            contact = contact_queryset.first()
            contact_of = Contact.objects.filter(phone_number=contact.phone_number).count()
            spam_of = Contact.objects.filter(phone_number=contact.phone_number, is_spam=True).count()
            spam_likelihood = 100 * spam_of / contact_of if contact_of != 0 else 0
            contact.spam_likelihood = spam_likelihood
            return contact
        
        # If neither user nor contact is found, raise a 404 error
        raise Http404("No object found matching the ID.")

class MarkSpamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({"error": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if phone_number==request.user.phone_number:
            return Response({"error": "Cannot set yourself as spam."}, status=status.HTTP_400_BAD_REQUEST)
            
        contact = Contact.objects.filter(user=request.user, phone_number=phone_number).first() 
        if contact:
            # If contact does not exist, create a new one
            contact.is_spam=True
            contact.save()
            return Response({"message": "Contact marked as spam."}, status=status.HTTP_201_CREATED)

        user = User.objects.filter(phone_number=phone_number).first()

        if user:
            user.spam_of += 1
            user.contact_of +=1
            user.save()
            contact = Contact(
                phone_number=phone_number,
                is_spam=True,
                name=user.name,
                user=request.user
            )
            contact.save()

            return Response({"message": "User spam count updated and contact saved."}, status=status.HTTP_200_OK)

        return Response({"message": "Phone number not found."}, status=status.HTTP_404_NOT_FOUND)

class GlobalView(generics.ListAPIView):
    serializer_class = GlobalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user_queryset, contact_queryset= get_global_database()
        return list(user_queryset) + list(contact_queryset)
