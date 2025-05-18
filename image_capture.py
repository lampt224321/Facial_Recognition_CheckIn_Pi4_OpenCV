import cv2
import os
from datetime import datetime

# Change this to the name of the person you're photographing
PERSON_NAME = "DuongHuyen"

# IP Webcam URL (replace with your phone IP)
IP_CAMERA_URL = "http://10.136.44.140:8080/video"  

def create_folder(name):
    dataset_folder = "dataset"
    if not os.path.exists(dataset_folder):
        os.makedirs(dataset_folder)
    
    person_folder = os.path.join(dataset_folder, name)
    if not os.path.exists(person_folder):
        os.makedirs(person_folder)
    return person_folder

def capture_photos(name):
    folder = create_folder(name)
    
    cap = cv2.VideoCapture(IP_CAMERA_URL)
    
    if not cap.isOpened():
        print("Khong ket noi duoc camera.")
        return

    photo_count = 0
    print(f"Taking photos for {name}. Press SPACE to capture, 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Khong nhan duoc khung hinh camera.")
            break

        
        cv2.imshow('Capture', frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '): 
            photo_count += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.jpg"
            filepath = os.path.join(folder, filename)
            cv2.imwrite(filepath, frame)
            print(f"Photo {photo_count} saved: {filepath}")
        
        elif key == ord('q'): 
            break

    
    cap.release()
    cv2.destroyAllWindows()
    print(f"Photo capture completed. {photo_count} photos saved for {name}.")

if __name__ == "__main__":
    capture_photos(PERSON_NAME)

