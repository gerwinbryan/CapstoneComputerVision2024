import torch
import torchvision.transforms as transforms
from torchvision.models import resnet18
import cv2
import numpy as np
from PIL import Image

class ColorDetector:
    def __init__(self):
        # Load pre-trained ResNet model
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = resnet18(pretrained=True)
        self.model.eval()
        self.model = self.model.to(self.device)

        # Define color classes
        self.color_classes = [
            'black', 'blue', 'brown', 'gray', 'green',
            'red', 'silver', 'white', 'yellow'
        ]

        # Mapping ImageNet classes to colors
        # These indices correspond to objects typically associated with these colors
        self.color_mapping = {
            'white': [
                403,  # white wolf
                604,  # jiffy limo (usually white)
                511,  # white shark
                898,  # white stork
            ],
            'black': [
                266,  # black widow
                267,  # black and gold garden spider
                827,  # black swan
                975,  # black grouse
            ],
            'red': [
                370,  # red fox
                933,  # red wine
                937,  # red cardinal
                944,  # red admiral butterfly
            ],
            'blue': [
                94,   # blue jay
                379,  # blue whale
                397,  # blue peafowl
                978,  # blue grouse
            ],
            'green': [
                982,  # green lizard
                983,  # green snake
                984,  # green mamba
                985,  # green iguana
            ],
            'yellow': [
                281,  # yellow lady slipper
                947,  # yellow warbler
                951,  # yellow finch
                957,  # bee eater (yellow bird)
            ],
            'brown': [
                167,  # brown bear
                206,  # brown swiss (cow)
                292,  # brown recluse spider
                300,  # grizzly (brown) bear
            ],
            'gray': [
                355,  # grey fox
                356,  # grey whale
                357,  # grey wolf
                358,  # alley cat (usually grey)
            ],
            'silver': [
                611,  # silver car
                612,  # sports car (often silver)
                817,  # steel arch bridge
                724,  # police vehicle (often silver)
            ]
        }

        # Image preprocessing
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def get_dominant_color(self, img):
        try:
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(img_rgb)
            
            # Preprocess image
            input_tensor = self.transform(pil_image)
            input_batch = input_tensor.unsqueeze(0).to(self.device)

            # Get model predictions
            with torch.no_grad():
                output = self.model(input_batch)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)

            # Calculate color scores
            color_scores = {}
            for color, indices in self.color_mapping.items():
                # Sum probabilities for each color's associated classes
                score = sum(probabilities[idx].item() for idx in indices)
                color_scores[color] = score

            # Get the color with highest score
            predicted_color = max(color_scores.items(), key=lambda x: x[1])
            
            # Print debug information
            print(f"Color scores: {color_scores}")
            print(f"Detected color: {predicted_color[0]}")
            print(f"Confidence: {predicted_color[1]:.4f}")
            
            # Simply return the highest confidence color
            return predicted_color[0]

        except Exception as e:
            print(f"Error in color detection: {str(e)}")
            return 'unknown'

    def download_weights(self):
        """
        Downloads the pre-trained weights if they don't exist.
        For ResNet18, this is handled automatically by torchvision.
        """
        pass
