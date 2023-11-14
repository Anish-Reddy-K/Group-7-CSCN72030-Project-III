import os
import cv2
import json
from facerec import SimpleFacerec

# Encode faces from a folder
sfr = SimpleFacerec()
sfr.load_encoding_images("trainingimages/")  

# Process all test images in the 'images' folder
test_images_folder = "images/"  # Change 'images' to the folder containing your test images
test_images = [f for f in os.listdir(test_images_folder) if f.endswith(('.jpg', '.jpeg', '.png'))]

for image_name in test_images:
    image_path = os.path.join(test_images_folder, image_name)
    frame = cv2.imread(image_path)
    detected_faces = sfr.detect_known_faces(frame)

    # Save the result to a JSON file if there are known faces
    if detected_faces:
        output_json_path = f"o{image_name[:-4]}.json"  # Output file name based on the input image
        with open(output_json_path, "w") as json_file:
            json.dump({"detected_faces": detected_faces}, json_file, indent=2)

        print(f"Detected faces' emails for {image_name} saved to {output_json_path}")
    else:
        print(f"No known faces detected in {image_name}")
