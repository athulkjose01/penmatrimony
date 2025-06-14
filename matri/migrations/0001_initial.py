# Generated by Django 5.2.3 on 2025-06-14 08:38

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='user_posts/')),
                ('caption', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('razorpay_order_id', models.CharField(max_length=100)),
                ('razorpay_payment_id', models.CharField(max_length=100)),
                ('razorpay_signature', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=15)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('post', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='matri.userpost')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=100)),
                ('gender', models.CharField(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], max_length=10)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('religion', models.CharField(default='Christian', editable=False, max_length=50)),
                ('category', models.CharField(default='Pentecost', editable=False, max_length=50)),
                ('mother_tongue', models.CharField(default='Malayalam', max_length=50)),
                ('marital_status', models.CharField(choices=[('Never Married', 'Never Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed'), ('Separated', 'Separated')], max_length=20)),
                ('height', models.IntegerField(blank=True, help_text='Height in Cm (e.g. 172)', null=True)),
                ('weight', models.IntegerField(blank=True, help_text='Weight in kg (e.g. 70)', null=True)),
                ('education', models.CharField(blank=True, max_length=100, null=True)),
                ('profession', models.CharField(blank=True, max_length=100, null=True)),
                ('Monthly_income', models.CharField(blank=True, max_length=50)),
                ('country', models.CharField(blank=True, default='India', max_length=50)),
                ('state', models.CharField(blank=True, default='Kerala', max_length=50)),
                ('city', models.CharField(blank=True, max_length=50)),
                ('housename', models.CharField(blank=True, max_length=50)),
                ('current_location', models.CharField(blank=True, max_length=50)),
                ('diet', models.CharField(blank=True, choices=[('Vegetarian', 'Vegetarian'), ('Non-Vegetarian', 'Non-Vegetarian')], max_length=20)),
                ('smoking', models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No'), ('Occasionally', 'Occasionally')], max_length=20)),
                ('drinking', models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No'), ('Occasionally', 'Occasionally')], max_length=20)),
                ('father_name', models.CharField(blank=True, max_length=100, null=True)),
                ('mother_name', models.CharField(blank=True, max_length=100, null=True)),
                ('family_status', models.CharField(blank=True, choices=[('Middle Class', 'Middle Class'), ('Upper Middle Class', 'Upper Middle Class'), ('Rich', 'Rich'), ('Affluent', 'Affluent')], max_length=50)),
                ('family_type', models.CharField(blank=True, choices=[('Joint', 'Joint'), ('Nuclear', 'Nuclear')], max_length=50)),
                ('siblings', models.PositiveIntegerField(blank=True, default=0, null=True)),
                ('looking_for', models.CharField(blank=True, choices=[('Male', 'Male'), ('Female', 'Female')], max_length=10)),
                ('about_me', models.TextField(blank=True, null=True)),
                ('hobbies', models.CharField(blank=True, max_length=255, null=True)),
                ('has_own_a_car', models.BooleanField(blank=True, null=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_pics/')),
                ('is_profile_in_index', models.BooleanField(default=False)),
                ('is_premium_member', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='userpost',
            name='user_profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='matri.userprofile'),
        ),
        migrations.CreateModel(
            name='PartnerPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('preferred_age_min', models.PositiveIntegerField(blank=True, null=True, verbose_name='Preferred Minimum Age')),
                ('preferred_age_max', models.PositiveIntegerField(blank=True, null=True, verbose_name='Preferred Maximum Age')),
                ('preferred_height_min', models.IntegerField(blank=True, help_text='e.g., 150 (in cm)', null=True, verbose_name='Preferred Min Height (cm)')),
                ('preferred_height_max', models.IntegerField(blank=True, help_text='e.g., 190 (in cm)', null=True, verbose_name='Preferred Max Height (cm)')),
                ('preferred_weight_min_kg', models.IntegerField(blank=True, help_text='e.g., 50 (in kg)', null=True, verbose_name='Preferred Min Weight (kg)')),
                ('preferred_weight_max_kg', models.IntegerField(blank=True, help_text='e.g., 80 (in kg)', null=True, verbose_name='Preferred Max Weight (kg)')),
                ('preferred_marital_status', models.CharField(blank=True, choices=[('Any', 'Any'), ('Never Married', 'Never Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed'), ('Separated', 'Separated')], default='Any', max_length=20, null=True, verbose_name='Preferred Marital Status')),
                ('preferred_education', models.CharField(blank=True, max_length=255, verbose_name='Preferred Education Level(s)')),
                ('preferred_profession', models.CharField(blank=True, max_length=255, verbose_name='Preferred Profession(s)')),
                ('preferred_diet', models.CharField(blank=True, choices=[('Any', 'Any'), ('Vegetarian', 'Vegetarian'), ('Non-Vegetarian', 'Non-Vegetarian')], default='Any', max_length=20, null=True, verbose_name='Preferred Diet')),
                ('preferred_smoking', models.CharField(blank=True, choices=[('Any', 'Any'), ('Yes', 'Yes'), ('No', 'No'), ('Occasionally', 'Occasionally')], default='Any', max_length=20, null=True, verbose_name='Preferred Smoking Habit')),
                ('preferred_drinking', models.CharField(blank=True, choices=[('Any', 'Any'), ('Yes', 'Yes'), ('No', 'No'), ('Occasionally', 'Occasionally')], default='Any', max_length=20, null=True, verbose_name='Preferred Drinking Habit')),
                ('expectations_about_partner', models.TextField(blank=True, verbose_name='A Few Words About Your Ideal Partner')),
                ('user_profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='partner_preferences', to='matri.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('participants', models.ManyToManyField(related_name='chat_rooms', to='matri.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='matri.chatroom')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to='matri.userprofile')),
            ],
            options={
                'ordering': ['timestamp'],
            },
        ),
        migrations.CreateModel(
            name='InterestRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_interests', to='matri.userprofile')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_interests', to='matri.userprofile')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('sender', 'receiver')},
            },
        ),
    ]
