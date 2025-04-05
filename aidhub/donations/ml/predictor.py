from geopy.geocoders import Nominatim
import numpy as np
import logging
from datetime import datetime, timedelta
from django.db.models import Avg, StdDev, Count
from django.utils import timezone
from ..models import Recipient, DonatedRecipient

logger = logging.getLogger('aidhub')

def get_coordinates(location):
    geolocator = Nominatim(user_agent="donation_ai")
    try:
        loc = geolocator.geocode(location)
        if loc:
            return loc.latitude, loc.longitude
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
    return None, None

def predict_urgency(location, donation_type):
    try:
        # Get statistics from both current and historical data
        current_stats = Recipient.objects.filter(donation_type=donation_type).aggregate(
            avg=Avg('urgency'),
            std=StdDev('urgency'),
            count=Count('id')
        )
        
        historical_stats = DonatedRecipient.objects.filter(
            donation_type=donation_type,
            transaction_date__gte=timezone.now() - timedelta(days=30)  # Last 30 days
        ).aggregate(
            avg=Avg('urgency'),
            std=StdDev('urgency'),
            count=Count('id')
        )
        
        # Calculate combined average
        current_avg = current_stats['avg'] or 0
        historical_avg = historical_stats['avg'] or 0
        combined_avg = (current_avg * 0.7 + historical_avg * 0.3) if historical_avg > 0 else current_avg
        
        if combined_avg > 0:
            # Calculate confidence based on multiple factors
            total_samples = (current_stats['count'] or 0) + (historical_stats['count'] or 0)
            data_confidence = min(0.8, total_samples / 20)  # Max 0.8 confidence from sample size
            
            # Calculate consistency confidence based on standard deviation
            current_std = current_stats['std'] or 0
            historical_std = historical_stats['std'] or 0
            avg_std = (current_std + historical_std) / 2 if historical_std > 0 else current_std
            consistency_confidence = max(0.2, 1 - (avg_std / 5))  # Lower std = higher confidence
            
            # Combine confidence factors
            final_confidence = (data_confidence * 0.6) + (consistency_confidence * 0.4)
            
            # Add some randomization to urgency
            urgency = max(1.5, min(5.0, combined_avg + np.random.normal(0, 0.3)))
            return urgency, final_confidence
        
        # Default values if no history, with low confidence
        return 3.0, 0.5
        
    except Exception as e:
        logger.error(f"Error in urgency prediction: {e}")
        return 3.0, 0.5
