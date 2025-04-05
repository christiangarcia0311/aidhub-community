from django.db import models
from datetime import datetime

class Recipient(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    donation_type = models.CharField(max_length=100)
    urgency = models.FloatField()
    contact = models.CharField(max_length=200)  # Email
    phone = models.CharField(max_length=20, blank=True)  # Add phone field
    message = models.TextField(blank=True, null=True)  # Add message field
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.donation_type}"

class Donation(models.Model):
    donor_name = models.CharField(max_length=200, blank=True, default='Anonymous Donor')
    donor_contact = models.CharField(max_length=200)  # Email
    donor_phone = models.CharField(max_length=20, blank=True)  # Add phone field
    donation_type = models.CharField(max_length=100)
    pickup_location = models.CharField(max_length=200)
    recipient = models.ForeignKey(Recipient, on_delete=models.CASCADE)
    donation_date = models.DateTimeField(auto_now_add=True)
    donation_image = models.ImageField(upload_to='donation_images/', null=True, blank=True)
    classified_type = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        if not self.donor_name:
            self.donor_name = 'Anonymous Donor'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.donor_name} to {self.recipient.name}"

class DonatedRecipient(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    donation_type = models.CharField(max_length=100)
    urgency = models.FloatField()
    donor_name = models.CharField(max_length=200, blank=True, default='Anonymous Donor')
    recipient_contact = models.CharField(max_length=200)  # Email
    recipient_phone = models.CharField(max_length=20, blank=True)  # Add phone field
    donor_contact = models.CharField(max_length=200)  # Email  
    donor_phone = models.CharField(max_length=20, blank=True)  # Add donor phone
    pickup_location = models.CharField(max_length=200)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.donor_name:
            self.donor_name = 'Anonymous Donor'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.donor_name} to {self.name}"
