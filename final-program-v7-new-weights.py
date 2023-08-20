import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
import threading
import serial
from tkinter import messagebox
import time
import re

rotate_code = 0
flip_code = 1
grid_division = 2

def change_grid_division(*args):
    global grid_division
    grid_division = int(selected_grid.get())

def draw_grid(frame):
    height = frame.shape[0]
    for i in range(1, grid_division):
        cv2.line(frame, (0, i * height // grid_division), (frame.shape[1], i * height // grid_division), (0,255,0), 2)
    return frame

def capture_frame():
    if connection_status.get() == "Terhubung":
        # rest of the capture_frame function
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
            
            # Load YOLOv4-tiny
            net = cv2.dnn.readNet("custom-yolov4-detector_final.weights", "custom-yolov4-detector.cfg")
            with open('obj.names', 'r') as f:
                classes = f.read().splitlines()

            # Start of YOLOv4 Inference
            img = cv2.imread("Output/Frame.png")
            img = cv2.resize(img, (720, 480), interpolation = cv2.INTER_CUBIC)
            frame_height = img.shape[0]
            # print("Image.shape", img.shape)
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
            print("ordered_class_ids:", ordered_class_ids)
            
            block_mapping = {
            "Blok Forward": "F",
            "Blok Left": "L",
            "Blok Open": "O",
            "Blok Reverse": "B",
            "Blok Right": "R",
            "Blok Close": "C",
            "Blok 10": "10",
            "Blok 20": "20",
            "Blok 30": "30",
            "Blok 40": "40",
            "Blok 45": "45",
            "Blok 50": "50",
            "Blok 60": "60",
            "Blok 90": "90",
            "Blok Start": "Start",
            "Blok Stop": "Stop"
            }
            
            def is_number(block_name):
                return block_name in ["10", "20", "30", "40", "45", "50", "60", "90"]

            def is_direction(block_name):
                return block_name in ["F", "L", "O", "B", "R", "C"]

            ordered_blocks = [block_mapping[classes[i]] for i in ordered_class_ids]
            output_blocks = []
            for i in range(len(ordered_blocks)):
                output_blocks.append(ordered_blocks[i])
                if i < len(ordered_blocks) - 1 and is_direction(ordered_blocks[i]) and is_number(ordered_blocks[i+1]):
                    output_blocks[i] += ordered_blocks[i+1]
                    ordered_blocks[i+1] = ""
                elif is_direction(ordered_blocks[i]):
                    output_blocks[i] += "0"

            output_blocks = [block for block in output_blocks if block != ""]

            print("output_blocks", output_blocks)
            if output_blocks[0] == 'Start' and output_blocks[-1] == 'Stop':
                with open('output.txt', 'w') as f:  
                    for block in output_blocks[1:-1]:
                        f.write(f"{block}\n")
                        
                ser = serial.Serial(port.get(), 9600)  # ganti 'COM4' dengan port yang sesuai
                time.sleep(2)  # memberi waktu untuk koneksi serial untuk membuka

                with open('output.txt', 'r') as f:
                    data = f.read().replace('\n', ',')  # baca file dan ganti newline dengan koma
                    print("Data yang dikirim ke robot:", data)

                ser.write(data.encode())  # kirim data
                # print(data)
                time.sleep(1)  # menunggu sedikit
                
                #Menampilkan serial monitor tapi gk akan pernah berhenti
                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8').rstrip()
                        print("Respon dari Arduino:", line)
                        
                        # Jika pesan khusus diterima, keluar dari loop
                        if line == "Semua Perintah Dijalankan":
                            break
                
                ser.close()  # tutup koneksi ketika selesai
                
                # for i in range(len(ordered_class_ids)):
                #     print(i+1, classes[ordered_class_ids[i]])
                #     with open('output.txt', 'w') as f:  # Open the file. 'w' means that the file will be overwritten if it exists.
                #         for i in range(len(ordered_class_ids)):
                #             # Write to the file instead of printing. The write() function doesn't add a newline at the end, so we add it manually.
                #             f.write(f"{i+1} {classes[ordered_class_ids[i]]}\n")

                # print("Ukuran Grid=", frame_height // grid_division)
                
                # Menampilkan gambar yang sudah dideteksi (berserta bounding box)
                # cv2.imshow("Image", img)
                # cv2.waitKey(0)
                # cv2.destroyAllWindows()
                # End of YOLOv4 Inference
            else:
                messagebox.showwarning("Peringatan", "Blok program tidak sesuai. Pastikan ada 'Start' di awal dan 'Stop' di akhir.")
    else:
        messagebox.showwarning("Peringatan", "Port COM belum terhubung!, silahkan cek koneksi terlebih dahulu")

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

def check_connection():
    global connection_status, port
    try:
        arduino = serial.Serial(port.get(), 9600, timeout=.1)
        arduino.close()
        connection_status.set("Terhubung dengan Robot")
    except:
        connection_status.set("Gagal/Tidak Terhubung")
        messagebox.showwarning("Peringatan", "Gagal Terhubung Silahkan cek atau pilih koneksi port COM lain")

window = tk.Tk()

# Frame Koneksi
frame_connection = tk.Frame(window)
frame_connection.pack(side="top", padx="10", pady="5")

connection_status = tk.StringVar(window, "Belum Terhubung Dengan Robot")
status_label = tk.Label(frame_connection, textvariable=connection_status)
status_label.grid(row=0, column=0, columnspan=3)

check_button = tk.Button(frame_connection, text="Cek Koneksi", command=check_connection)
check_button.grid(row=1, column=0)

OPTIONS_PORT = ["COM3", "COM4", "COM5", "COM7"]
port = tk.StringVar(window)
port.set(OPTIONS_PORT[0])
label_port = tk.Label(frame_connection, text="Pilih Port COM:")
label_port.grid(row=1, column=1)
dropdown_port = tk.OptionMenu(frame_connection, port, *OPTIONS_PORT)
dropdown_port.grid(row=1, column=2)

# Frame Kontrol
frame_controls = tk.Frame(window)
frame_controls.pack(side="top", padx="10", pady="5")

capture_button = tk.Button(frame_controls, text="Capture Frame", command=capture_frame)
capture_button.grid(row=0, column=0)

rotate_button = tk.Button(frame_controls, text="Rotate Frame", command=rotate_frame)
rotate_button.grid(row=0, column=1)

flip_button = tk.Button(frame_controls, text="Flip Frame", command=flip_frame)
flip_button.grid(row=0, column=2)

# Frame Pengaturan
frame_settings = tk.Frame(window)
frame_settings.pack(side="top", padx="10", pady="5")

OPTIONS_WEBCAM = ["0", "1", "2"]
selected_webcam = tk.StringVar(window)
selected_webcam.set(OPTIONS_WEBCAM[0])
label_webcam = tk.Label(frame_settings, text="Pilih Webcam:")
label_webcam.grid(row=0, column=0)
dropdown_webcam = tk.OptionMenu(frame_settings, selected_webcam, *OPTIONS_WEBCAM, command=change_webcam)
dropdown_webcam.grid(row=0, column=1)

OPTIONS_GRID = ["1", "2", "3", "4", "5"]
selected_grid = tk.StringVar(window)
selected_grid.set(OPTIONS_GRID[1])
label_grid = tk.Label(frame_settings, text="Pembagian Grid:")
label_grid.grid(row=1, column=0)
dropdown_grid = tk.OptionMenu(frame_settings, selected_grid, *OPTIONS_GRID, command=change_grid_division)
dropdown_grid.grid(row=1, column=1)

# Preview Webcam
cap = cv2.VideoCapture(0)
lmain = tk.Label(window)
lmain.pack()

# Run the webcam feed in a thread
threading.Thread(target=show_frame).start()

# Run the window loop
window.mainloop()