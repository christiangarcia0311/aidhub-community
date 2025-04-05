import torch
import torchvision.transforms as transforms
from torchvision.models import resnet18
from PIL import Image
import io
import logging

logger = logging.getLogger('aidhub')

# Categories for donation classification
DONATION_CATEGORIES = [
    'clothes', 'medicine', 'food', 'electronics', 'books',
    'toys', 'furniture', 'hygiene', 'supplies', 'appliances', 'other'
]

class DonationImageClassifier:
    """
    Sample images that work well for each category:
    
    1. Clothes (indices 400-460, 600-620):
        - T-shirts, pants, dresses laid flat
        - Hanging clothing items
        - Stacked folded clothes
        - Shoes, jackets, hats
    
    2. Medicine (indices 520-530, 847-849):
        - Medicine bottles/containers
        - First aid kits
        - Medical supplies like bandages
        - Medical equipment
        
    3. Food (indices 920-960, 980-990):
        - Canned goods
        - Packaged food items
        - Fresh produce
        - Boxed food products
        
    4. Electronics (indices 500-540):
        - Mobile phones
        - Laptops/computers
        - Chargers/cables
        - Small appliances
        
    5. Books (indices 970-980):
        - Textbooks
        - Novels/reading books
        - Stacked books
        - Educational materials
        
    6. Toys (indices 850-870):
        - Action figures
        - Board games
        - Stuffed animals
        - Building blocks/legos
        
    7. Furniture (indices 750-780):
        - Chairs/tables
        - Beds/mattresses
        - Cabinets/shelves
        - Home furniture items
        
    8. Hygiene (indices 630-650):
        - Toiletries
        - Soap/shampoo bottles
        - Personal care items
        - Cleaning supplies
        
    9. Supplies (indices 460-500, 760-770):
        - School supplies
        - Office materials
        - Stationery items
        - General household supplies
        
    10. Appliances (indices 540-580):
        - Kitchen appliances
        - Home electronics
        - Household machines
        - Power tools
    
    Image Requirements:
    - Clear, well-lit photos
    - Single category per image
    - Centered subject
    - Minimal background clutter
    - RGB format
    - Reasonable size (recommended 256x256 or larger)
    """
    
    def __init__(self):
        try:
            # Load a lightweight pre-trained ResNet18 model
            self.device = torch.device('cpu')
            self.model = resnet18(pretrained=True)
            self.model.eval()
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            logger.info("Image classification model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading image classification model: {e}")
            self.model = None

    def preprocess_image(self, image_data):
        try:
            # Handle different types of image inputs
            if hasattr(image_data, 'read'):  # Django uploaded file
                image = Image.open(image_data)
            elif isinstance(image_data, (bytes, io.BytesIO)):
                image = Image.open(io.BytesIO(image_data))
            else:
                image = Image.open(image_data)

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply transformations
            return self.transform(image).unsqueeze(0).to(self.device)
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return None

    def classify_image(self, image_data):
        try:
            if self.model is None:
                return "other", 0.0

            # Preprocess image
            processed_image = self.preprocess_image(image_data)
            if processed_image is None:
                return "other", 0.0

            # Get predictions
            with torch.no_grad():
                output = self.model(processed_image)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                confidence, predicted = torch.max(probabilities, 0)

            # Map ImageNet category to donation category
            mapped_category = self.map_to_donation_category(predicted.item())
            
            return mapped_category, float(confidence)

        except Exception as e:
            logger.error(f"Error classifying image: {e}")
            return "other", 0.0
            
    def map_to_donation_category(self, class_idx):
        try:
            # Enhanced category mappings with more specific ranges
            category_mappings = {
                'clothes': list(range(400, 460)) + list(range(600, 620)),
                'food': list(range(920, 960)) + list(range(980, 990)),
                'electronics': list(range(500, 540)),
                'medicine': list(range(520, 530)) + [847, 848, 849], # Add medical supply indices
                'books': list(range(970, 980)),
                'toys': list(range(850, 870)),
                'furniture': list(range(750, 780)),
                'hygiene': list(range(630, 650)),
                'supplies': list(range(460, 500)) + list(range(760, 770)), # General supplies
                'appliances': list(range(540, 580)) # Home appliances
            }
            
            # First check for exact matches
            for category, indices in category_mappings.items():
                if class_idx in indices:
                    return category
            
            # If no exact match, check closest category based on distance
            min_distance = float('inf')
            best_category = 'other'
            
            for category, indices in category_mappings.items():
                for idx in indices:
                    distance = abs(class_idx - idx)
                    if distance < min_distance:
                        min_distance = distance
                        best_category = category
            
            # Only use closest category if reasonably close
            if min_distance <= 20:
                return best_category
                    
            return 'other'
            
        except Exception as e:
            logger.error(f"Error mapping category: {e}")
            return 'other'

classifier = DonationImageClassifier()
