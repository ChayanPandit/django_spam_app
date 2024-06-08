from rest_framework import serializers
from .models import User, Contact
from django.contrib.auth import authenticate
from rest_framework.validators import UniqueValidator


class UserSerializer(serializers.ModelSerializer):
    spam_likelihood = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'name', 'phone_number', 'password', 'spam_likelihood']
        extra_kwargs = {'password': {'write_only': True}}

    def get_spam_likelihood(self, obj):
        if isinstance(obj, User):
            if obj.contact_of != 0:
                return 100* obj.spam_of / obj.contact_of
            else:
                return 0        
        else:  # Assuming it's a Contact object
            contact_of = Contact.objects.filter(phone_number=obj.phone_number).count()
            spam_of = Contact.objects.filter(phone_number=obj.phone_number, is_spam=True).count()
            return 100 * spam_of / contact_of if contact_of != 0 else 0
    
    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return user
        
        
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'phone_number', 'is_spam']


class GlobalSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=255)
    is_user = serializers.BooleanField()
    spam_likelihood = serializers.SerializerMethodField()

    def get_spam_likelihood(self, obj):
        if obj.get('contact_of', 0) != 0:
            return 100 * obj.get('spam_of', 0) / obj.get('contact_of', 0)
        else:
            return 0
