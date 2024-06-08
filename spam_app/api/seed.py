import random, faker
from django.contrib.auth import get_user_model
from .models import Contact
User = get_user_model()

fake = faker.Faker()


def seed_users(n=10)->None:
    try:
        for _ in range(0,n):
        
            name = fake.name()
            phone_number = fake.phone_number()
            while User.objects.filter(phone_number=phone_number).exists():
                phone_number = fake.phone_number()

            email = random.choice(['',fake.email()])
            password = fake.password()
        
            user = User.objects.create(
                name = name,
                phone_number = phone_number,
                email = email,
                password = password,
                contact_of = 0,
                spam_of = 0,
            )
            
            print(f'Created user: {user}')
            
    except Exception as e:
        print(e)
        

def seed_contacts(contacts_per_user=5, no_of_real_contacts=3) -> None:
        # Get all users after creation
        all_users = list(User.objects.all())

        # Create Contacts for each User
        for user in all_users:
            existing_users = random.sample(all_users, min(no_of_real_contacts, len(all_users)))
            for existing_user in existing_users:
                if existing_user != user and not Contact.objects.filter(user=user, phone_number=existing_user.phone_number).exists():
                    
                    print(existing_user)
                    
                    is_spam=random.choice([True, False])
                    contact = Contact.objects.create(
                        user=user,
                        name=existing_user.name,
                        phone_number=existing_user.phone_number,
                        is_spam=is_spam,
                    )
                    
                    existing_user.contact_of +=1
                    if is_spam:
                        existing_user.spam_of +=1
                    
                    existing_user.save()

                    print(f'Created contact from existing user: {contact}')

            # Fill the rest with fake contacts
            for _ in range(contacts_per_user - len(existing_users)):
                contact_name = fake.name()
                contact_phone_number = fake.phone_number()
                
                while Contact.objects.filter(user=user, phone_number=contact_phone_number).exists():
                    contact_phone_number = fake.phone_number()
                
                is_spam=random.choice([True, False])

                contact = Contact.objects.create(
                    user=user,
                    name=contact_name,
                    phone_number=contact_phone_number,
                    is_spam=is_spam
                )
                
                existing_user = User.objects.filter(phone_number=contact_phone_number).first()
                if existing_user:
                    existing_user.contact_of +=1
                    if is_spam:
                        existing_user.spam_of +=1
                        
                    existing_user.save()
                  
                
                print(f'Created fake contact: {contact}')
                


def seed_all():
    seed_users()
    seed_contacts()
