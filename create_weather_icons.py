from PIL import Image, ImageDraw
import os

os.makedirs("images/weather", exist_ok=True)

# Clear/Sunny icon
img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.ellipse([16, 16, 48, 48], fill=(255, 200, 50))
for i in range(8):
    angle = i * 45
    import math

    x1 = 32 + int(28 * math.cos(math.radians(angle)))
    y1 = 32 + int(28 * math.sin(math.radians(angle)))
    x2 = 32 + int(36 * math.cos(math.radians(angle)))
    y2 = 32 + int(36 * math.sin(math.radians(angle)))
    d.line([(x1, y1), (x2, y2)], fill=(255, 200, 50), width=3)
img.save("images/weather/clear.png")

# Rain icon
img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.ellipse([10, 15, 30, 30], fill=(150, 150, 150))
d.ellipse([25, 10, 50, 30], fill=(130, 130, 130))
d.ellipse([18, 22, 42, 40], fill=(150, 150, 150))
for i in range(5):
    x = 15 + i * 8
    d.line([(x, 42), (x - 2, 54)], fill=(100, 150, 255), width=2)
img.save("images/weather/rain.png")

# Cloudy icon
img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.ellipse([8, 20, 28, 35], fill=(200, 200, 200))
d.ellipse([24, 15, 52, 35], fill=(180, 180, 180))
d.ellipse([16, 28, 48, 48], fill=(200, 200, 200))
img.save("images/weather/cloudy.png")

print("Weather icons created successfully!")
