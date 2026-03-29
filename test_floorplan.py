import cv2
import numpy as np

# Create a simple floor plan image
width, height = 800, 600
image = np.ones((height, width, 3), dtype=np.uint8) * 255

# Draw outer walls (rectangle)
cv2.rectangle(image, (100, 100), (700, 500), (0, 0, 0), 8)

# Draw interior walls
# Horizontal walls
cv2.line(image, (100, 300), (400, 300), (0, 0, 0), 6)
cv2.line(image, (400, 300), (700, 300), (0, 0, 0), 6)

# Vertical walls  
cv2.line(image, (400, 100), (400, 300), (0, 0, 0), 6)
cv2.line(image, (400, 300), (400, 500), (0, 0, 0), 6)

# Add some interior walls for rooms
cv2.line(image, (250, 100), (250, 300), (0, 0, 0), 4)
cv2.line(image, (550, 300), (550, 500), (0, 0, 0), 4)

# Draw door openings (gaps in walls)
cv2.line(image, (250, 200), (250, 220), (255, 255, 255), 8)  # Door opening
cv2.line(image, (380, 300), (420, 300), (255, 255, 255), 8)  # Door opening

# Save the image
cv2.imwrite('test_floorplan.png', image)
print("Test floor plan created: test_floorplan.png")
