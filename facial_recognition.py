import face_recognition
import cv2
import numpy as np
import time
import pickle
import os
import threading
from datetime import datetime
import csv
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from gpiozero import LED
from collections import deque
import multiprocessing

# Configuration
CAMERA_URL = "http://10.136.44.208:8080/video"  # Replace with your camera URL
CHECKIN_FILE = "checkin_log.csv"
IMG_FOLDER = "checkin_images"
cv_scaler = 8  # Increased scale factor for faster processing (was 6)
GPIO_PIN = 14  # GPIO pin for access control

# Performance optimization settings
SKIP_FRAMES = 2  # Process every nth frame (skip frames for speed)
MAX_FACES = 3    # Maximum number of faces to process per frame
RECOGNITION_TOLERANCE = 0.6  # Face recognition tolerance (higher = faster but less accurate)
FRAME_BUFFER_SIZE = 5  # Size of frame buffer for smoothing

# Setup directories and files 
if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

if not os.path.exists(CHECKIN_FILE):
    with open(CHECKIN_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Timestamp"])

# Initialize GPIO
try:
    output = LED(GPIO_PIN)
    gpio_available = True
    print(f"GPIO initialized on pin {GPIO_PIN}")
except:
    gpio_available = False
    print("GPIO not available, running in software-only mode")

# Load face encodings
print("[INFO] Loading encodings...")
try:
    with open("encodings.pickle", "rb") as f:
        data = pickle.loads(f.read())
    known_face_encodings = data["encodings"]
    known_face_names = data["names"]
    print(f"Loaded {len(known_face_names)} face encodings")
    
    # Convert to numpy array for faster processing
    known_face_encodings = np.array(known_face_encodings)
    
except Exception as e:
    print(f"Error loading encodings: {e}")
    exit()

# List of names that will trigger the GPIO pin (authorize access)
authorized_names = {"TungLam", "Nanh", "MinhHuyen", "DuongHuyen"}  # Use set for O(1) lookup

# Function to show Tkinter messagebox in a separate thread
def show_message_box(name, is_authorized=False):
    def run():
        root = tk.Tk()
        root.withdraw()
        if is_authorized:
            messagebox.showinfo("✅ AUTHORIZED", f"Access granted for: {name}")
        else:
            messagebox.showinfo("✅ CHECK-IN", f"Check-in completed for: {name}")
        root.destroy()
    
    # Run in a separate thread to not block the main process
    message_thread = threading.Thread(target=run)
    message_thread.daemon = True
    message_thread.start()

class OptimizedFaceRecognition:
    def __init__(self, video_label=None, status_callback=None):
        self.video_label = video_label
        self.status_callback = status_callback
        self.running = False
        self.cap = None
        
        # Check-in status variables
        self.checkin_done = False
        self.last_checkin_time = 0
        self.cooldown_period = 5
        
        # FPS calculation variables
        self.frame_count = 0
        self.fps = 0
        self.fps_start_time = time.time()
        
        # Optimization variables
        self.frame_counter = 0
        self.last_face_locations = []
        self.last_face_names = []
        self.face_tracking_buffer = deque(maxlen=FRAME_BUFFER_SIZE)
        
        # Async processing
        self.processing_queue = multiprocessing.Queue(maxsize=3)
        self.result_queue = multiprocessing.Queue(maxsize=3)
        self.processing_active = False
        
    def connect_camera(self):
        """Connect to the camera with optimized settings"""
        print(f"[INFO] Attempting to connect to camera at {CAMERA_URL}")
        self.cap = cv2.VideoCapture(CAMERA_URL)
        
        # Try to open default camera if URL fails
        if not self.cap.isOpened():
            print("[INFO] Cannot connect to IP camera, trying default camera...")
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("[ERROR] Cannot connect to any camera")
                return False
        
        # Optimize camera settings for performance
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer size
        self.cap.set(cv2.CAP_PROP_FPS, 30)  # Set FPS
        
        # Try to set resolution for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 400)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 300)
        
        print("[INFO] Camera connected successfully")
        return True
        
    def start(self):
        """Start the face recognition process"""
        if self.running:
            return
            
        self.running = True
        
        if not self.connect_camera():
            if self.status_callback:
                self.status_callback("Failed to connect to camera")
            return False
        
        # Start async processing
        self.start_async_processing()
        
        # Start main processing thread
        self.process_thread = threading.Thread(target=self.process_video)
        self.process_thread.daemon = True
        self.process_thread.start()
        return True
        
    def start_async_processing(self):
        """Start async face recognition processing"""
        self.processing_active = True
        self.processor = multiprocessing.Process(target=self.async_face_processor)
        self.processor.daemon = True
        self.processor.start()
        
    def stop(self):
        """Stop the face recognition process"""
        self.running = False
        self.processing_active = False
        
        if hasattr(self, 'processor'):
            self.processor.terminate()
            self.processor.join(timeout=1)
            
        if self.cap:
            self.cap.release()
        
        # Turn off GPIO pin when stopping
        if gpio_available:
            output.off()
            
    def calculate_fps(self):
        """Calculate and return the current FPS"""
        self.frame_count += 1
        elapsed_time = time.time() - self.fps_start_time
        if elapsed_time > 1.0:
            self.fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.fps_start_time = time.time()
        return self.fps
        
    def async_face_processor(self):
        """Async face recognition processor"""
        while self.processing_active:
            try:
                # Get frame from queue with timeout
                if not self.processing_queue.empty():
                    frame_data = self.processing_queue.get(timeout=0.1)
                    
                    # Process the frame
                    face_locations, face_names = self.recognize_faces(frame_data)
                    
                    # Put result back
                    if not self.result_queue.full():
                        self.result_queue.put((face_locations, face_names))
                        
            except:
                continue
                
    def recognize_faces(self, rgb_frame):
        """Fast face recognition on a frame"""
        # Find faces with optimized settings
        face_locations = face_recognition.face_locations(
            rgb_frame, 
            number_of_times_to_upsample=1,  # Reduced for speed
            model="hog"  # HOG is faster than CNN
        )
        
        # Limit number of faces to process
        face_locations = face_locations[:MAX_FACES]
        
        face_names = []
        
        if face_locations:
            # Get face encodings with optimized model
            face_encodings = face_recognition.face_encodings(
                rgb_frame, 
                face_locations, 
                model='small'  # Use small model for speed
            )
            
            # Process each face
            for face_encoding in face_encodings:
                # Fast face comparison using vectorized operations
                if len(known_face_encodings) > 0:
                    # Calculate distances all at once
                    face_distances = np.linalg.norm(known_face_encodings - face_encoding, axis=1)
                    
                    # Find best match
                    best_match_index = np.argmin(face_distances)
                    
                    if face_distances[best_match_index] <= RECOGNITION_TOLERANCE:
                        name = known_face_names[best_match_index]
                    else:
                        name = "Unknown"
                else:
                    name = "Unknown"
                    
                face_names.append(name)
        
        return face_locations, face_names
        
    def process_video(self):
        """Process video frames with optimization"""
        try:
            while self.running:
                # Capture frame
                ret, frame = self.cap.read()
                if not ret:
                    print("[ERROR] Failed to read frame. Retrying...")
                    if self.status_callback:
                        self.status_callback("Camera error, retrying...")
                    time.sleep(0.1)
                    
                    # Try to reconnect
                    self.cap.release()
                    if gpio_available:
                        output.off()
                    self.connect_camera()
                    continue
                
                # Calculate FPS
                current_fps = self.calculate_fps()
                
                # Skip frames for performance
                self.frame_counter += 1
                if self.frame_counter % SKIP_FRAMES == 0:
                    # Prepare frame for processing
                    small_frame = cv2.resize(frame, (0, 0), fx=1/cv_scaler, fy=1/cv_scaler)
                    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    
                    # Send to async processor if queue not full
                    if not self.processing_queue.full():
                        try:
                            self.processing_queue.put_nowait(rgb_frame)
                        except:
                            pass
                
                # Get results from async processor
                if not self.result_queue.empty():
                    try:
                        self.last_face_locations, self.last_face_names = self.result_queue.get_nowait()
                        self.face_tracking_buffer.append((self.last_face_locations, self.last_face_names))
                        
                        # Handle check-ins and GPIO
                        self.handle_recognitions(frame)
                    except:
                        pass
                
                # Use smoothed results for display
                smooth_locations, smooth_names = self.get_smoothed_results()
                
                # Draw results on the frame
                display_frame = self.draw_results(frame, smooth_locations, smooth_names, current_fps)
                
                # Display frame in UI
                self.update_display(display_frame)
                
        except Exception as e:
            print(f"[ERROR] Error in face recognition: {e}")
            if self.status_callback:
                self.status_callback(f"Error: {str(e)}")
        finally:
            self.cleanup()
    
    def get_smoothed_results(self):
        """Get smoothed face detection results"""
        if not self.face_tracking_buffer:
            return [], []
            
        # Use most recent result for simplicity
        # You could implement more sophisticated smoothing here
        return self.face_tracking_buffer[-1]
    
    def handle_recognitions(self, frame):
        """Handle recognized faces for check-ins and GPIO control"""
        current_time = time.time()
        authorized_face_detected = False
        
        for name in self.last_face_names:
            if name in authorized_names:
                authorized_face_detected = True
                
                # Show message if we haven't recently
                if current_time - self.last_checkin_time > self.cooldown_period:
                    show_message_box(name, is_authorized=True)
                    self.last_checkin_time = current_time
            
            # Handle check-in
            if name != "Unknown" and (not self.checkin_done or 
                                     (current_time - self.last_checkin_time > self.cooldown_period)):
                
                now = datetime.now()
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                filename = f"{name}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                filepath = os.path.join(IMG_FOLDER, filename)
                
                # Save image in thread to avoid blocking
                threading.Thread(
                    target=lambda: cv2.imwrite(filepath, frame),
                    daemon=True
                ).start()
                
                # Log check-in in thread
                threading.Thread(
                    target=self.log_checkin,
                    args=(name, timestamp),
                    daemon=True
                ).start()
                
                self.checkin_done = True
                self.last_checkin_time = current_time
                
                if name not in authorized_names:
                    show_message_box(name)
                
                if self.status_callback:
                    self.status_callback(f"Check-in successful: {name}")
        
        # Control GPIO
        if gpio_available:
            if authorized_face_detected:
                output.on()
            else:
                output.off()
    
    def log_checkin(self, name, timestamp):
        """Log check-in to CSV file"""
        try:
            with open(CHECKIN_FILE, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([name, timestamp])
        except Exception as e:
            print(f"Error logging check-in: {e}")
    
    def draw_results(self, frame, face_locations, face_names, fps):
        """Draw recognition results on the frame"""
        # Display FPS
        cv2.putText(frame, f"FPS: {fps:.1f}", (frame.shape[1] - 150, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Display processing info
        cv2.putText(frame, f"Faces: {len(face_locations)}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.putText(frame, f"Scale: 1/{cv_scaler}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Draw boxes and labels for each face
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations
            top *= cv_scaler
            right *= cv_scaler
            bottom *= cv_scaler
            left *= cv_scaler
            
            # Draw box around face
            box_color = (0, 255, 0) if name in authorized_names else (244, 42, 3)
            cv2.rectangle(frame, (left, top), (right, bottom), box_color, 3)
            
            # Draw label
            cv2.rectangle(frame, (left - 3, top - 35), (right + 3, top), box_color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (0, 0, 0), 1)
            
            # Add authorization indicator
            if name in authorized_names:
                cv2.putText(frame, "Authorized", (left + 6, bottom + 23), font, 1.0, (0, 255, 0), 1)
        
        return frame
    
    def update_display(self, display_frame):
        """Update the UI display with the frame"""
        if self.video_label:
            try:
                # Convert to RGB
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                
                # Resize for display
                label_width = self.video_label.winfo_width()
                label_height = self.video_label.winfo_height()
                
                if label_width > 1 and label_height > 1:
                    img = img.resize((label_width, label_height), Image.LANCZOS)
                
                # Update display
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.config(image=imgtk)
            except Exception as e:
                print(f"Display update error: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.cap:
            self.cap.release()
        if gpio_available:
            output.off()
        self.running = False

# Alias for backward compatibility
FaceRecognition = OptimizedFaceRecognition

def main():
    root = tk.Tk()
    root.mainloop()

if __name__ == "__main__":
    main()