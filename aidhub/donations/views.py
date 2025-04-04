from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.db.models import Count, Avg
from django.core.exceptions import ObjectDoesNotExist
from .models import Recipient, Donation, DonatedRecipient
from .ml.predictor import predict_urgency, get_coordinates
from .ml.trainer import train_model, train_trend_model
from geopy.distance import geodesic
import json
import logging
from .ml.image_classifier import classifier  # Add this import
from django.views.decorators.csrf import csrf_exempt  # Add this import
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger('aidhub')

class IndexView(View):
    def get(self, request):
        return render(request, 'donations/index.html')

class TrendingView(View):
    def get(self, request):
        try:
            trends = Recipient.objects.values('donation_type') \
                                   .annotate(count=Count('id')) \
                                   .order_by('-count')[:3]
            
            trend_list = []
            for trend in trends:
                trend_list.append({
                    "type": trend['donation_type'].capitalize(),
                    "count": trend['count'],
                    "message": f"{trend['donation_type'].capitalize()} (requested {trend['count']} times)"
                })
            
            return JsonResponse({
                "message": "Current Donation Needs",
                "trends": trend_list
            })
        except Exception as e:
            logger.error(f"Error getting trends: {e}")
            return JsonResponse({
                "message": "Error getting trends",
                "trends": []
            })

class RecipientListView(View):
    def get(self, request):
        donation_type = request.GET.get('type', '').lower()
        donor_location = request.GET.get('location', '')
        
        if not donation_type or not donor_location:
            return JsonResponse({"error": "Missing donation type or location"}, status=400)
        
        try:
            donor_lat, donor_lon = get_coordinates(donor_location)
            if donor_lat is None:
                return JsonResponse({"error": "Invalid location"}, status=400)
            
            recipients = Recipient.objects.filter(donation_type=donation_type)
            if not recipients:
                return JsonResponse({"error": "No matching recipients found"}, status=404)
            
            recipient_list = []
            for recipient in recipients:
                confidence = predict_urgency(recipient.location, recipient.donation_type)[1]
                # Calculate distance
                distance = geodesic(
                    (donor_lat, donor_lon),
                    (recipient.latitude, recipient.longitude)
                ).km
                
                recipient_list.append({
                    'id': recipient.id,
                    'name': recipient.name,
                    'location': recipient.location,
                    'latitude': recipient.latitude,
                    'longitude': recipient.longitude,
                    'donation_type': recipient.donation_type,
                    'urgency': recipient.urgency,
                    'contact': recipient.contact,
                    'confidence': confidence,
                    'distance': distance,  # Add distance to response
                    'message': recipient.message  # Include message in response
                })
            
            # Sort by distance and urgency
            recipient_list.sort(key=lambda x: (x['distance'] * 0.3) - (x['urgency'] * 0.7))
            
            return JsonResponse({
                "recipients": recipient_list,
                "donor_coordinates": {
                    "latitude": donor_lat,
                    "longitude": donor_lon
                },
                "donor_location": donor_location
            })
        except Exception as e:
            logger.error(f"Error listing recipients: {e}")
            return JsonResponse({"error": str(e)}, status=500)

class DonationView(View):
    def post(self, request):
        try:
            # Log request headers and body
            logger.info(f"Received donation request. Content-Type: {request.headers.get('Content-Type')}")
            logger.info(f"Request body: {request.body.decode()}")
            
            # Parse JSON data
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return JsonResponse({
                    "success": False,
                    "error": "Invalid JSON data provided"
                }, status=400)

            # Validate required fields - remove donor_name from required fields
            required = ['donor_contact', 'donor_phone', 'donation_type', 
                       'donor_location', 'pickup_location', 'recipient_id']
            
            missing_fields = [field for field in required if not data.get(field)]
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                return JsonResponse({
                    "success": False,
                    "error": error_msg
                }, status=400)
                
            try:
                recipient_id = int(data['recipient_id'])
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid recipient ID: {data.get('recipient_id')} - {e}")
                return JsonResponse({
                    "success": False,
                    "error": "Invalid recipient ID format"
                }, status=400)
            
            try:
                recipient = Recipient.objects.get(id=recipient_id)
                logger.info(f"Found recipient: {recipient.id} - {recipient.name}")
            except Recipient.DoesNotExist:
                error_msg = f"Recipient not found with ID: {recipient_id}"
                logger.error(error_msg)
                return JsonResponse({
                    "success": False,
                    "error": error_msg
                }, status=404)

            # Use transaction to ensure data consistency
            from django.db import transaction
            try:
                with transaction.atomic():
                    # Create the records - use data.get() for donor_name to handle empty values
                    donated = DonatedRecipient.objects.create(
                        name=recipient.name,
                        location=recipient.location,
                        latitude=recipient.latitude,
                        longitude=recipient.longitude,
                        donation_type=recipient.donation_type,
                        urgency=recipient.urgency,
                        donor_name=data.get('donor_name', ''),  # Use get() with empty default
                        recipient_contact=recipient.contact,
                        donor_contact=data['donor_contact'],
                        donor_phone=data['donor_phone'],
                        recipient_phone=recipient.phone,
                        pickup_location=data['pickup_location']
                    )
                    
                    donation = Donation.objects.create(
                        donor_name=data.get('donor_name', ''),  # Use get() with empty default
                        donor_contact=data['donor_contact'],
                        donor_phone=data['donor_phone'],
                        donation_type=data['donation_type'].lower(),
                        pickup_location=data['pickup_location'],
                        recipient=recipient
                    )
                    
                    # Delete recipient only after successful creation
                    recipient.delete()
                    logger.info(f"Donation successful: {donation.id}")

                    # Send emails after successful donation
                    self.send_donation_emails(
                        donor_name=data.get('donor_name', 'Anonymous Donor'),
                        donor_email=data['donor_contact'],
                        donor_phone=data['donor_phone'],  # Add donor_phone
                        recipient_name=recipient.name,
                        recipient_email=recipient.contact,
                        recipient_phone=recipient.phone,  # Add recipient phone
                        donation_type=data['donation_type'],
                        pickup_location=data['pickup_location'],
                        delivery_location=recipient.location,
                        message=data.get('message', '')
                    )

                    return JsonResponse({
                        "success": True,
                        "message": "Donation successful",
                        "details": {
                            "donor": data.get('donor_name', 'Anonymous Donor'),
                            "recipient": recipient.name,
                            "type": data['donation_type']
                        }
                    })
                    
            except Exception as e:
                logger.error(f"Database transaction error: {str(e)}")
                return JsonResponse({
                    "success": False,
                    "error": "Database error occurred while processing donation"
                }, status=500)

        except Exception as e:
            logger.error(f"Unexpected error in donation processing: {str(e)}")
            return JsonResponse({
                "success": False,
                "error": "An unexpected error occurred while processing your donation"
            }, status=500)

    def send_donation_emails(self, donor_name, donor_email, donor_phone, recipient_name, 
                           recipient_email, recipient_phone, donation_type, pickup_location, 
                           delivery_location, message):
        try:
            # Send email to donor
            donor_subject = 'Thank you for your donation!'
            donor_message = f"""
Thank you for your donation!

Dear {donor_name},

Thank you for your generous donation of {donation_type}. 
Your contribution will make a real difference in someone's life.

Your Message:
{message or "No message provided"}

Pickup Details
- Location: {pickup_location}

Recipient Information  
- Name: {recipient_name}
- Email: {recipient_email}
- Phone: {recipient_phone or 'Not provided'}
- Delivery Location: {delivery_location}

Please coordinate with the recipient to arrange the transfer of your donation.

Thank you for making a difference in your community!

Best regards,
AidHub Team
"""
            
            send_mail(
                subject=donor_subject,
                message=donor_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[donor_email],
                fail_silently=False,
            )

            # Send email to recipient
            recipient_subject = 'Good news! Your donation request has been matched'
            recipient_message = f"""
Donation Match Notification

Dear {recipient_name},

Great news! Your request for {donation_type} has been matched with a donor.

Donor Information
- Name: {donor_name}
- Email: {donor_email} 
- Phone: {donor_phone or 'Not provided'}
- Pickup Location: {pickup_location}

Donor's Message:
{message or "No message provided"}

Please coordinate with the donor to arrange the pickup/delivery of your donation.

Best regards,
AidHub Team
"""

            send_mail(
                subject=recipient_subject,
                message=recipient_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )

            logger.info(f"Donation emails sent successfully to {donor_email} and {recipient_email}")

        except Exception as e:
            logger.error(f"Error sending donation emails: {str(e)}")
            # Don't raise the exception to prevent transaction rollback
            # But log it for debugging
            pass

class AddRecipientView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            required = ['name', 'location', 'donation_type', 'contact', 'phone']  # Add phone requirement
            
            if not all(field in data for field in required):
                return JsonResponse({"error": "Missing required fields"}, status=400)
            
            latitude, longitude = get_coordinates(data['location'])
            if latitude is None:
                return JsonResponse({"error": "Invalid location"}, status=400)
            
            urgency, confidence = predict_urgency(data['location'], data['donation_type'])
            
            recipient = Recipient.objects.create(
                name=data['name'],
                location=data['location'],
                latitude=latitude,
                longitude=longitude,
                donation_type=data['donation_type'].lower(),
                urgency=urgency,
                contact=data['contact'],
                phone=data.get('phone', ''),  # Add phone number
                message=data.get('message', '')  # Changed from request_message to message
            )
            
            # Retrain models
            train_model()
            train_trend_model()
            
            return JsonResponse({
                "success": True,
                "message": f"Recipient added successfully! Urgency level {urgency:.2f}/5.0 (confidence: {confidence:.2%})",
                "urgency": urgency,
                "confidence": confidence
            })
            
        except Exception as e:
            logger.error(f"Error adding recipient: {e}")
            return JsonResponse({"error": str(e)}, status=500)

class HistoryView(View):
    def get(self, request):
        try:
            transactions = DonatedRecipient.objects.all().order_by('-transaction_date')
            type_stats = DonatedRecipient.objects.values('donation_type') \
                                                .annotate(
                                                    count=Count('id'),
                                                    avg_urgency=Avg('urgency')
                                                ) \
                                                .order_by('-count')
            
            transaction_list = []
            for t in transactions:
                transaction_list.append({
                    "recipient_name": t.name,
                    "location": t.location,
                    "donation_type": t.donation_type,
                    "donor_name": t.donor_name,
                    "recipient_contact": t.recipient_contact,
                    "donor_contact": t.donor_contact,
                    "pickup_location": t.pickup_location,
                    "date": t.transaction_date
                })
            
            stats_list = []
            for stat in type_stats:
                stats_list.append({
                    "donation_type": stat['donation_type'].capitalize(),
                    "count": stat['count'],
                    "avg_urgency": float(stat['avg_urgency'])
                })
            
            return JsonResponse({
                "transactions": transaction_list,
                "type_stats": stats_list
            })
            
        except Exception as e:
            logger.error(f"Error getting donation history: {e}")
            return JsonResponse({
                "transactions": [],
                "type_stats": [],
                "error": str(e)
            })

class SummaryStatsView(View):
    def get(self, request):
        try:
            # Get total donations by combining current donations and donated history
            total_donations = (
                Donation.objects.count() + 
                DonatedRecipient.objects.count()
            )
            
            # Get unique donors by combining both tables and using distinct
            unique_donors = len(set(
                list(Donation.objects.values_list('donor_name', flat=True)) +
                list(DonatedRecipient.objects.values_list('donor_name', flat=True))
            ))
            
            # Get unique communities served
            communities_served = len(set(
                list(Recipient.objects.values_list('location', flat=True)) +
                list(DonatedRecipient.objects.values_list('location', flat=True))
            ))
            
            return JsonResponse({
                'total_donations': total_donations,
                'unique_donors': unique_donors,
                'communities_served': communities_served
            })
            
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            return JsonResponse({
                'total_donations': 0,
                'unique_donors': 0,
                'communities_served': 0
            })

class ClassifyImageView(View):  # Add this new view class
    def post(self, request):
        try:
            if 'image' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'message': 'No image file provided'
                }, status=400)

            image_file = request.FILES['image']
            category, confidence = classifier.classify_image(image_file)

            return JsonResponse({
                'success': True,
                'category': category,
                'confidence': confidence
            })
        except Exception as e:
            logger.error(f"Error classifying image: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@csrf_exempt
def current_needs(request):
    try:
        # Get all active recipient requests
        recipients = Recipient.objects.all()
        needs = [
            {
                'donation_type': r.donation_type,
                'urgency': r.urgency,
                'location': r.location
            } 
            for r in recipients
        ]
        
        return JsonResponse({
            'success': True,
            'needs': needs
        })
    except Exception as e:
        logger.error(f"Error fetching current needs: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error fetching current needs'
        }, status=500)
