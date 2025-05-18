# Facial_Recognition_CheckIn_Pi4_OpenCV
This project is about Check-In system with OpenCV and Raspberry 4

# 🔐 Facial Recognition Check-In System with LED Door Simulation

This project uses **face recognition** to simulate a **door opening/closing mechanism** using an **LED** on a Raspberry Pi 4. Once a face is successfully recognized from the dataset, the system will activate a GPIO pin to turn on the LED—mimicking a successful check-in and door access.

---

## 📦 1. Environment Setup

To keep the environment clean and dependencies manageable, it's recommended to use a **virtual environment**.

### ✅ Steps:

1. Create a folder `Face_Recognition` (or your preferred name), and place the 4 project scripts inside.
2. Open a terminal inside that folder.
3. Run the following commands:

```bash
# Create virtual environment
python3 -m venv myenv

# Activate virtual environment
source myenv/bin/activate

# Update packages and install required libraries
sudo apt update
pip install opencv-python
pip install imutils
sudo apt install cmake
pip install face-recognition
````

> ⚠️ Installing `face-recognition` can take a while. Be patient—it’s normal.

---

## 📸 2. Camera Setup and Image Collection

The system uses an **IP Camera** connected to the Raspberry Pi. You need to configure the camera stream URL inside:

* `image_capture.py`
* `facial_recognition.py`

➡️ Instructions are embedded in the scripts.

### 🧾 Image Capture Instructions:

```bash
python3 image_capture.py
```

* Press `SPACE` to capture an image.
* Press `Q` to quit.
* Name each image folder according to the person being captured (In the image_capture.py).
* Capture **9–12 images** per person (more is better).

---

## 🧠 3. Train the Model

Once your dataset is ready:

```bash
python3 model_training.py
```

This will process the images and prepare a trained encoding for each registered face.

---

## 🚀 4. Run the Facial Recognition System

```bash
python3 facial_recognition_ui.py
```

When a registered face is detected, the LED will turn ON to simulate door access.

---

## 📱 5. (Optional) Create a GUI App on Raspberry Pi OS

To run the application without using the terminal:

1. Create a `.desktop` file:

```bash
nano ~/.local/share/applications/facial_checkin.desktop
```

2. Add the following content (adjust paths as needed):

```ini
[Desktop Entry]
Version=1.0
Name=Facial Check-In
Exec=bash -c "source /path/to/Face_Recognition/myenv/bin/activate && python3 /path/to/Face_Recognition/facial_recognition_ui.py"
Icon=/path/to/icon.png
Path=/path/to/Face_Recognition
Type=Application
Terminal=false
Categories=Utility,Application;
```

3. Grant execution permission:

```bash
chmod +x ~/.local/share/applications/facial_checkin.desktop
```

Now you can run the application directly from the **menu** without using the terminal.

> ⚠️ Note: You still need to use the terminal for adding new face images and retraining the model.

---

## 🔌 6. Connect LED to Raspberry Pi GPIO

**Wiring Diagram:**

```
Raspberry Pi (Pin 8 - GPIO 14) ---> [Anode LED]
                                     |
                                 [Cathode LED]
                                     |
                              [220Ω Resistor]
                                     |
                      Raspberry Pi (Pin 14 - GND)
```

![Raspberry Pi 4 GPIO Pinout](Raspberry-Pi-4-Pinout.png)

> 📌 **Important**: Make sure to modify the `facial_recognition.py` script to include the names (as strings) that exactly match those used during image capture.

---

## ⚠️ Final Notes

* This project demonstrates a simplified door access system using **face recognition + hardware interaction**.
* It is suitable for demonstrations, academic use, and prototyping.

---


