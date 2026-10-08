"""Render a plain text fixture for reproducible OCR checks (no AI generation)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
font_paths = ['/System/Library/Fonts/Supplemental/Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
font_path = next((path for path in font_paths if Path(path).exists()), None)
font = ImageFont.truetype(font_path, 32) if font_path else ImageFont.load_default(size=32)
heading = ImageFont.truetype(font_path, 42) if font_path else ImageFont.load_default(size=42)
image = Image.new('RGB', (1400, 730), 'white')
draw = ImageDraw.Draw(image)
draw.text((65, 55), 'ATLAS RESEARCH - OCR PRACTICE', fill='black', font=heading)
lines = [
    'Fictional sample image for testing document research.',
    '',
    'The workshop coordinator is Elena Brooks.',
    'The workshop location is Cedar Room.',
    'The workshop starts at 3 PM on Friday.',
    'The workshop registration fee is 25 dollars.',
    'The workshop capacity is 18 attendees.',
    '',
    'The equipment checklist includes a projector and a laptop.',
    'No coordinator phone number is provided in this image.',
]
for index, line in enumerate(lines):
    draw.text((65, 150 + index * 49), line, fill='black', font=font)
path = ROOT / 'data/practice-workshop.png'
image.save(path)
print(path)
