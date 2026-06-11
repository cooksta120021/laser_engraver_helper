#!/usr/bin/env python3
"""
Create a simple icon for the Engraver Helper application.
Uses PIL to create a laser/wood themed icon.
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create a simple 256x256 icon and save as .ico file."""
    
    # Create 256x256 image with transparent background
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple laser/wood icon
    # Wood plank background
    draw.rectangle([20, 100, 236, 180], fill=(139, 90, 43, 255), outline=(101, 67, 33, 255), width=3)
    
    # Wood grain lines
    for y in range(110, 170, 10):
        draw.line([30, y, 226, y+2], fill=(101, 67, 33, 255), width=2)
    
    # Laser beam
    draw.polygon([(128, 40), (118, 80), (138, 80)], fill=(255, 0, 0, 255))
    draw.line([128, 80, 128, 140], fill=(255, 100, 100, 255), width=4)
    
    # Laser head
    draw.ellipse([108, 20, 148, 60], fill=(100, 100, 100, 255), outline=(50, 50, 50, 255), width=3)
    
    # Engraved area on wood
    draw.ellipse([110, 130, 146, 150], fill=(80, 50, 25, 255))
    
    # Save as ICO file
    img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Icon created: icon.ico")

if __name__ == "__main__":
    create_icon()
