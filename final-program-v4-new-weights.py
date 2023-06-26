import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
import threading

rotate_code = 0
flip_code = 1
grid_division = 2

# Load YOLOv4-tiny
net = cv2.dnn.readNet("custom-yolov4-detector_final.weights", "custom-yolov4-detector.cfg")
with open('obj.names', 'r') as f:
    classes = f.read().splitlines()

def change_grid_division(*args):
    global grid_division
    grid_division = int(selected_grid.get())

def draw_grid(frame):
    height = frame.shape[0]
    for i in range(1, grid_division):
        cv2.line(frame, (0, i * height // grid_division), (frame.shape[1], i * height // grid_division), (0,255,0), 2)
    return frame

def capture_frame():
    global cap, rotate_code, flip_code
    ret, frame = cap.read()
    if ret:
        frame = cv2.flip(frame, flip_code)
        if rotate_code == 1:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotate_code == 2:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif rotate_code == 3:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        cv2.imwrite('Output/Frame.png', frame)

        # Start of YOLOv4 Inference
        img = cv2.imread("Output/Frame.png")
        img = cv2.resize(img, (720, 480), interpolation = cv2.INTER_CUBIC)
        frame_height = img.shape[0]
        print(img.shape)
        height, width, channel = img.shape

        blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop = False)
        net.setInput(blob)
        outs = net.forward(net.getUnconnectedOutLayersNames())

        class_ids = []
        confidences = []
        boxes = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    # Rectangle coordinates
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # Applying Non-Maximum Suppression
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

        font = cv2.FONT_HERSHEY_PLAIN
        for i in range(len(boxes)):
            if i in indexes:
                x, y, w, h = boxes[i]
                label = str(classes[class_ids[i]])
                confidence = str(round(confidences[i], 2))  # Convert the confidence score to string and round it to 2 decimal places
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(img, label, (x, y + 30), font, 1, (0, 0, 0), 2)
                cv2.putText(img, confidence, (x, y + 50), font, 1, (0, 0, 0), 2)  # Display the confidence score
                
        # define a function to define the sort key
        def sort_key(index):
            x, y, _, _ = boxes[index]
            # use a tuple, first sort by y, then by x
            return (y // (frame_height // grid_division), x)

        # Now class_ids are in the order of objects in the image
        ordered_class_ids = []
        if len(indexes) > 0:  # Check if there are detected objects
            # Sort by top to bottom and then left to right
            indexes = sorted(indexes.flatten(), key=sort_key)
            ordered_class_ids = [class_ids[i] for i in indexes]
            
        for i in range(len(ordered_class_ids)):
            print(i+1, classes[ordered_class_ids[i]])
            with open('output.txt', 'w') as f:  # Open the file. 'w' means that the file will be overwritten if it exists.
                for i in range(len(ordered_class_ids)):
                    # Write to the file instead of printing. The write() function doesn't add a newline at the end, so we add it manually.
                    f.write(f"{i+1} {classes[ordered_class_ids[i]]}\n")

        print("Ukuran Grid=", frame_height // grid_division)
        
        cv2.imshow("Image", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        # End of YOLOv4 Inference

def rotate_frame():
    global rotate_code
    rotate_code = (rotate_code + 1) % 4

def flip_frame():
    global flip_code
    flip_code *= -1

def change_webcam(*args):
    global cap
    cap.release()
    cap = cv2.VideoCapture(int(selected_webcam.get()))

def show_frame():
    global cap, rotate_code, flip_code
    _, frame = cap.read()
    frame = cv2.flip(frame, flip_code)
    if rotate_code == 1:
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotate_code == 2:
        frame = cv2.rotate(frame, cv2.ROTATE_180)
    elif rotate_code == 3:
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    frame = draw_grid(frame)
    cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
    img = Image.fromarray(cv2image)
    imgtk = ImageTk.PhotoImage(image=img)
    lmain.imgtk = imgtk
    lmain.configure(image=imgtk)
    lmain.after(100, show_frame) 

window = tk.Tk()

# Add a capture button
capture_button = tk.Button(window, text="Capture Frame", command=capture_frame)
capture_button.pack(side="bottom", fill="both", expand="yes", padx="10", pady="10")

# Add a rotate button
rotate_button = tk.Button(window, text="Rotate Frame", command=rotate_frame)
rotate_button.pack(side="bottom", fill="both", expand="yes", padx="10", pady="10")

# Add a flip button
flip_button = tk.Button(window, text="Flip Frame", command=flip_frame)
flip_button.pack(side="bottom", fill="both", expand="yes", padx="10", pady="10")

# Add a dropdown menu to select the webcam
OPTIONS = ["0", "1", "2"] # add more if you have more webcams
selected_webcam = tk.StringVar(window)
selected_webcam.set(OPTIONS[0]) # default value
dropdown = tk.OptionMenu(window, selected_webcam, *OPTIONS, command=change_webcam)
dropdown.pack()

# Add a dropdown menu to select the grid division
OPTIONS = ["1", "2", "3", "4", "5"] # adjust this to fit your needs
selected_grid = tk.StringVar(window)
selected_grid.set(OPTIONS[1]) # default value
dropdown = tk.OptionMenu(window, selected_grid, *OPTIONS, command=change_grid_division)
dropdown.pack()

# Add a webcam feed
cap = cv2.VideoCapture(0)
lmain = tk.Label(window)
lmain.pack()

# Run the webcam feed in a thread
threading.Thread(target=show_frame).start()

# Run the window loop
window.mainloop()