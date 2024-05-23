import cv2
import numpy as np
from tkinter import *
from PIL import Image, ImageTk

class ChessViz:
    ARUCO_DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    CHESS_DICT = {
        0: 'p', 
        1: 'B', 
        2: 'N', 
        3: 'k', 
        4: 'Q', 
        5: 'P', 
        6: 'b', 
        7: 'r', 
        8: 'K', 
        9: 'q', 
        10: 'n', 
        11: 'R'
    }
    
    def __init__(self, big_crop, small_crop, cam_index=1):
        self.big_crop = big_crop                        # [[y value, x value], sidelength]
        self.small_crop = small_crop                    # [[y value, x value], sidelength]
        self.cam_index = cam_index
        
        # find origin of small relative to big
        self.y_origin = self.small_crop[0][0] - self.big_crop[0][0]
        self.x_origin = self.small_crop[0][1] - self.big_crop[0][1]
        if self.x_origin < 0 or self.y_origin < 0:
            raise Exception("big crop's origin must be larger in both x and y")
        
        # takes picture and determines resolution width and height
        # from picture dimensions
        cam = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        ret, image = cam.read() 
        self.resolution_width = image.shape[1]
        self.resolution_height = image.shape[0] 
        
    # For tkinter gui
    def __update_crop_params(self, crop_params, x_var, y_var, sidelength_var):
        crop_params[0][1] = int(x_var.get())
        crop_params[0][0] = int(y_var.get())
        crop_params[1] = int(sidelength_var.get())

    # For tkinter gui
    def __show_frame(self, crop_params, cap, lmain):
        _, frame = cap.read()
        cropped_frame = frame[crop_params[0][0]:(crop_params[0][0] + crop_params[1]), 
                            crop_params[0][1]:(crop_params[0][1] + crop_params[1])]
        cv_img = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv_img)
        imgtk = ImageTk.PhotoImage(image=img)
        lmain.imgtk = imgtk
        lmain.configure(image=imgtk)
        lmain.after(10, lambda: self.__show_frame(crop_params, cap, lmain))

    # Uses tkinter gui to help dev find crop parameters, i.e. crop origin, 
    # crop width, and crop height
    def crop_gui(self, crop_id):
        if crop_id == 0: 
            crop_params = self.big_crop
        elif crop_id == 1:
            crop_params = self.small_crop
            
        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)

        root = Tk()
        root.bind('<Escape>', lambda e: root.quit())
        lmain = Label(root)
        lmain.pack()

        # Sliders for cropping parameters
        frame_x = Frame(root)
        frame_x.pack(fill='x', expand=True)
        x_var = StringVar()
        x_slider = Scale(frame_x, from_=0, to=self.resolution_width - 1, 
                         orient=HORIZONTAL, variable=x_var, label="X Origin")
        x_entry = Entry(frame_x, textvariable=x_var, width=5)
        x_slider.pack(side='left')
        x_entry.pack(side='left')

        frame_y = Frame(root)
        frame_y.pack(fill='x', expand=True)
        y_var = StringVar()
        y_slider = Scale(frame_y, from_=0, to=self.resolution_height - 1, 
                         orient=HORIZONTAL, variable=y_var, label="Y Origin")
        y_entry = Entry(frame_y, textvariable=y_var)
        y_slider.pack(side='left')
        y_entry.pack(side='left')

        frame_sidelength = Frame(root)
        frame_sidelength.pack(fill='x', expand=True)
        sidelength_var = StringVar()
        sidelength_var_slider = Scale(frame_sidelength, from_=1, to=self.resolution_width - 1, 
                             orient=HORIZONTAL, variable=sidelength_var, 
                             label="Crop Sidelength")
        sidelength_var_entry = Entry(frame_sidelength, textvariable=sidelength_var)
        sidelength_var_slider.pack(side='left')
        sidelength_var_entry.pack(side='left')
        
        # Button to update cropping parameters
        button = Button(root, text="Update Crop", 
                        command=lambda: self.__update_crop_params(
                            crop_params, x_var, y_var, sidelength_var))
        button.pack()
        root.bind('<Return>', lambda event: self.__update_crop_params(
            crop_params, x_var, y_var, sidelength_var))

        self.__show_frame(crop_params, cap, lmain)  # Start showing the frame
        root.mainloop()  # Start the GUI

        cap.release()
            
    def get_image(self):
        cam = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
        result, image = cam.read()
        cam.release()
        if not result: 
            raise "Error taking image"
        
        return image
    
    def get_crop(self, image, crop_params):
        return image[crop_params[0][0]:(crop_params[0][0] + crop_params[1]), 
                        crop_params[0][1]:(crop_params[0][1] + crop_params[1])]

    # TODO: Uses canny edge detection to set crop_width, crop_height,
    # and crop_origin automatically
    def find_chessboard():
        pass
        
    def get_center(self, corners):
        corners = corners.reshape((4, 2))
        (top_left, top_right, bottom_right, bottom_left) = corners
        
        # Convert the (x,y) coordinate pairs to integers
        top_right = (int(top_right[0]), int(top_right[1]))
        bottom_right = (int(bottom_right[0]), int(bottom_right[1]))
        bottom_left = (int(bottom_left[0]), int(bottom_left[1]))
        top_left = (int(top_left[0]), int(top_left[1]))
    
        # Calculate and draw the center of the ArUco marker
        center_y = int((top_left[0] + bottom_right[0]) / 2.0)
        center_x = int((top_left[1] + bottom_right[1]) / 2.0)
        return (center_y, center_x)
    
    def modified_step(self, value, div, min, max):
        value = value // div
        if value > max:
            value = max
        if value < min:
            value = min
            
        return value
            
    def get_chess_piece(self, center_y, center_x, id, chess_array):
        # subtract relative origin of small from centers
        center_y = center_y - self.y_origin
        center_x = center_x - self.x_origin
        
        # divide center y and x by square width to acquire
        # square coordinates
        square_len = self.small_crop[1] // 8
        center_y = self.modified_step(center_y, square_len, 0, 7)
        center_x = self.modified_step(center_x, square_len, 0, 7)
        
        # convert square coordinates to chess array 
        chess_array[center_y, center_x] = self.CHESS_DICT[id[0]]
        return chess_array

    def resize_image(self, image, factor):
        # Get the original image dimensions
        h, w = image.shape[:2]
        return cv2.resize(image, (round(factor * w), round(factor * h)))

    def test_aruco_detection(self):
        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
        total = 0
        detected = 0

        while(cap.isOpened()):
            chess_array = np.full((8, 8), '', dtype='U1')
            ret, frame = cap.read()
            frame = self.get_crop(frame, self.big_crop) 
            frame = self.resize_image(frame, 1)
            total += 1
            # Detect ArUco markers in the video frame
            (corners, ids, rejected) = cv2.aruco.detectMarkers(frame, self.ARUCO_DICT)
            if len(corners) == 32:
                detected += 1
            
            print(ids)
            if len(corners) > 0:
                # Flatten the ArUco IDs list
                # ids = ids.flatten()
                # # Loop over the detected ArUco corners
                for (marker_corner, marker_id) in zip(corners, ids):
            
                    # Extract the marker corners
                    corners = marker_corner.reshape((4, 2))
                    (top_left, top_right, bottom_right, bottom_left) = corners
                    
                    # Convert the (x,y) coordinate pairs to integers
                    top_right = (int(top_right[0]), int(top_right[1]))
                    bottom_right = (int(bottom_right[0]), int(bottom_right[1]))
                    bottom_left = (int(bottom_left[0]), int(bottom_left[1]))
                    top_left = (int(top_left[0]), int(top_left[1]))
                    
                    # Draw the bounding box of the ArUco detection
                    cv2.line(frame, top_left, top_right, (0, 255, 0), 2)
                    cv2.line(frame, top_right, bottom_right, (0, 255, 0), 2)
                    cv2.line(frame, bottom_right, bottom_left, (0, 255, 0), 2)
                    cv2.line(frame, bottom_left, top_left, (0, 255, 0), 2)
                    
                    # Calculate and draw the center of the ArUco marker
                    center_y = int((top_left[0] + bottom_right[0]) / 2.0)
                    center_x = int((top_left[1] + bottom_right[1]) / 2.0)
                    cv2.circle(frame, (center_y, center_x), 4, (0, 0, 255), -1)
                    
                    # Draw the ArUco marker ID on the video frame
                    # The ID is always located at the top_left of the ArUco marker
                    cv2.putText(frame, str(marker_id), 
                    (top_left[0], top_left[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 2)
                    self.get_chess_piece(center_y, center_x, marker_id, chess_array)
                    
            # Display the resulting frame
            cv2.imshow('frame', frame)
            print(chess_array)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
        cv2.destroyAllWindows()
        cap.release()
            
        print("percent detected: ", 100 * detected / total, "%")