import tkinter as tk
from tkinter import ttk
from tkinter import font
from PIL import Image
from tkinter import messagebox
import sqlite3
from os.path import isfile
import os
import cv2
from picamera.array import PiRGBArray
from picamera import PiCamera
import numpy as np
import pickle
import shutil
import numpy as np
import threading
import os.path
import queue
import RPi.GPIO as GPIO
from pad4pi import rpi_gpio 

# gpio pins for solenoid lock
relay = 18
GPIO.setwarnings(False)
GPIO.setup(relay, GPIO.OUT)
GPIO.output(relay, 0)

# queue to put key presses for external keypad
q = queue.Queue()
# directory where file is in
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# database file
file = os.path.join(BASE_DIR, "database.db")

# initializing values for the virtual keypad
keys = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

# values of external keypad
KEYPAD = [
    ['1','2','3','A'],
    ['4','5','6','B'],
    ['7','8','9','C'],
    ['*','0','#','D']
]

# tries is how many attempts and inp is empty string to input key presses
tries = 0
inp = ""

# GLOBAL VARIABLES THAT CAN BE USED IN OTHER FRAMES
PIN = ""
USERNAME = ""
PASSCODE = ""
ID = ""

# example of how to call function in other classes
# use ex) command = lambda: print_things(self,user)
# def print_things(self, name):
#     print(name)

# def speak_accept(self):
#     os.system("espeak 'User Accepted, Welcome' ")

# def speak_denied(self):
#     os.system("espeak 'User Denied, Going back to Home Screen' ")

# def speak_start(self):
#     os.system("espeak 'Welcome to the Facial Recognition Lock System. As a New User, Please Press the Button Below to get Started' ")

# def speak_info(self):
#     os.system("espeak 'Please Enter your name and passcode to get started' ")

# End the program
def end(self):
    self.controller.destroy()

# Functino to train the trainer with the users inputted into the database
def train(self):
    faceCascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    recognizer = cv2.faceCascade.LBPHFaceRecognizer_create()

    baseDir = os.path.dirname(os.path.abspath(__file__))
    imageDir = os.path.join(baseDir, 'images')

    currentId = 1
    labelIds = {}
    yLabels = []
    xTrain = []

    for root, dirs, files, in os.walk(imageDir):
        print(root, dirs, files)
        for file in files:
            print(file)
            
            if file.endswith("png") or file.endswith("jpg"):
                path = os.path.join(root, file)
                label = os.path.basename(root)
                print(label)
                
                if not label in labelIds:
                    labelIds[label] = currentId
                    print(labelIds)
                    currentId += 1
                
                id = labelIds[label]
                pilImage = Image.open(path).convert("L")
                imageArray = np.array(pilImage, "uint8")
                faces = faceCascade.detectMultiScale(imageArray,
                                                     minNeighbors = 5
                                                     )
                
                for (x,y,w,h) in faces:
                    roi = imageArray[y:y+h, x:x+w]
                    xTrain.append(roi)
                    yLabels.append(id)

    with open("labels", "wb") as f:
        pickle.dump(labelIds, f)
        f.close()
        
    recognizer.train(xTrain, np.array(yLabels))
    recognizer.save("trainer.yml")
    print(labelIds)

# Function to capture the images of the new user being added into the database
def cap(self, name, _id):
    def take(count, dirName, name):
        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 30
        rawCapture = PiRGBArray(camera, size=(640, 480))
        face_detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        for frame in camera.capture_continuous(rawCapture, format = "bgr", use_video_port = True):
            # Breaks out of loop to close the camera when there are more images than the number that is set
            if count > 20:
                cv2.destroyAllWindows()
                break
            frame = frame.array
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # changes to gray
            faces = face_detector.detectMultiScale(
                gray,
                scaleFactor = 1.2,
                minNeighbors = 5
                )

            for(x,y,w,h) in faces:
                roiGray = gray[y:y+h,x:x+w]
                fileName = dirName + "/" + name + " "+ str(count) + ".jpg"
                cv2.imwrite(fileName, roiGray)
                cv2.imshow("face", roiGray)
                cv2.rectangle(frame, (x,y), (x+w, y+h), (255,0,0), 2)
                count += 1

            cv2.imshow('frame', frame)
            key = cv2.waitKey(100) & 0xff
            rawCapture.truncate(0)

            if key == 27:
                break
        print("Camera Turning Off")
        cv2.destroyAllWindows()
        camera.close()

    # ID is shown first for ordering sake, will not actually interfere with recognizer
    dirName = "./images/" + str(_id) + " " + name
    print(dirName)
    if not os.path.exists(dirName):
        os.makedirs(dirName)
    print("Directory Created")

    print("\n[INFO] Initializing face capture. Look at camera and wait...")
    self.controller.after(2000, take, 1, dirName, name)

# Function to recognize the user when user uses face scan to access lock
def recognize(self, i):
    def rec(i):
        def denied():
            self.controller.show_frame("Denied")    # will show denied frame
            #self.controller.after(100, denied_thread(self))
        def home():
            self.controller.show_frame("HomeScreen")    # Will show homescreen frame
            self.controller.after(3000, end, self)
        def show():
            self.controller.show_frame("Successful")    #W display successful frame
            #self.controller.after(100, accept_thread(self))

        # function to unlock the door
        def unlock():
            print("Door is unlocked")
            GPIO.output(18, GPIO.HIGH)
        # Function to lock the door
        def lock():
            print("Door is locked")
            GPIO.output(18, GPIO.LOW)
            self.controller.after(100, home)

       # Where the pi would speak, but not enough power, so left out 
 
        # def accept_thread(self):
        #     t1 = threading.Thread(target=speak_accept, args=(self,))
        #     t1.start()
        #     t1.join()
        
        # def denied_thread(self):
        #     t2 = threading.Thread(target=speak_denied, args=(self,))
        #     t2.start()
        #     t2.join()
            
        with open('labels', 'rb') as f:
            dict = pickle.load(f)
            f.close()

        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 30
        rawCapture = PiRGBArray(camera, size = (640, 480))

        faceCascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read("trainer.yml")  # loads the trainer file
        ex = True
        for frame in camera.capture_continuous(rawCapture, format = "bgr", use_video_port = True):
            frame = frame.array
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor = 1.2,
                minNeighbors = 5,
                minSize= (300,300),
                )

            for(x,y,w,h) in faces:
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)
                _id,confidence = recognizer.predict(gray[y:y+h, x:x+w])
                for name, value in dict.items():
                    if value == _id:
                        print(name)
                        print(str(confidence))
                        if i == 6:
                            print("Too many tries, exiting program")
                            self.controller.after(500, denied)  # Shows denied frame
                            cv2.destroyAllWindows()
                            self.controller.after(6000, home)   # Goes to homescreen frame after 6 seconds
                            ex = False
                            break
                        if confidence <= 40:    # Checks to see if the recognizer finds a user that is close to user that is getting face scanned
                            print("Welcome: " + name + "\nUnlocking door")
                            self.controller.after(1000, show)   # Will show the successful frame
                            self.controller.after(1010, unlock) # after a millisecond, will unlock the door
                            self.controller.after(9000, lock)   # will lock the door after 9 seconds
                            cv2.destroyAllWindows()
                            ex = False
                            break
                        else:
                            print("Unknown,Please trying again!")
                            i+=1
                break # breaks out loop so that the camera closes properly when user is recognized or not
            
            cv2.imshow('frame', frame)
            key = cv2.waitKey(1)
            rawCapture.truncate(0)
            if ex == False:
                break
            if key == 27:
                break
            #break
        print("Camera being turned off")
        cv2.destroyAllWindows()
        camera.close()

    self.controller.after(3000, rec, i)

# same as recognizer function, but this is for specific user
def scan(self, i, _id):
    def take(i, _id):
        def denied():
            self.controller.show_frame("Denied")   
            #self.controller.after(100, denied_speak(self))
        def home():
            self.controller.show_frame("HomeScreen")
        def show():
            self.controller.show_frame("Successful")
            #self.controller.after(100, accept_speak(self))
        def unlock():
            print("Door is unlocked")
            GPIO.output(18, GPIO.HIGH)  # disengage lock
        def lock():
            print("Door is locked")
            GPIO.output(18, GPIO.LOW)   # re-engage lock
            self.controller.after(100, home)

        # Where system would speak, but lack of power prevents this

        # def accept_speak(self):
        #     t1 = threading.Thread(target=speak_accept, args=(self,))
        #     t1.start()
        #     t1.join()
        
        # def denied_speak(self):
        #     t2 = threading.Thread(target=speak_denied, args=(self,))
        #     t2.start()
        #     t2.join()
            
        with open('labels', 'rb') as f:
            dict = pickle.load(f)
            f.close()

        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 30
        rawCapture = PiRGBArray(camera, size = (640, 480))

        faceCascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read("trainer.yml")  # Load trainer file
        ex = True
        for frame in camera.capture_continuous(rawCapture, format = "bgr", use_video_port = True):
            frame = frame.array
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = faceCascade.detectMultiScale(
                gray,
                scaleFactor = 1.2,
                minNeighbors = 5,
                minSize= (300,300),
                )

            for(x,y,w,h) in faces:
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)
                _,confidence = recognizer.predict(gray[y:y+h, x:x+w])
                for name, value in dict.items():
                    if value == _id:
                        print(name)
                        print(str(confidence))
                        if i == 6:
                            print("Too many tries, exiting program")
                            self.controller.after(500, denied)  # shows denied screen
                            cv2.destroyAllWindows()
                            self.controller.after(6000, home)   # taken back to homescreen after 6 seconds
                            ex = False
                            break
                        if confidence <= 40:
                            print("Welcome: " + name + "\nUnlocking door")
                            self.controller.after(500, show)    # Shows successful frame
                            self.controller.after(1010, unlock) # disengages lock
                            self.controller.after(9000, lock)   # locks door after 9 seconds
                            cv2.destroyAllWindows()
                            ex = False
                            break
                        else:
                            print("Unknown,Please trying again!")
                            i+=1
                break   # used to break loop and close PiCamera
            
            cv2.imshow('frame', frame)
            key = cv2.waitKey(1)
            rawCapture.truncate(0)
            if ex == False:
                break
            if key == 27:
                break
            #break
        print("Camera being turned off")
        cv2.destroyAllWindows()
        camera.close()

    self.controller.after(3000, take, i, _id)
    
# Face scan to access the user's profile
def scan_profile(self, i, _id):
    def take(i, _id):
        def denied():
            self.controller.show_frame("ProfileDenied")
        def accept():
            self.controller.show_frame("ProfileAccepted")
        def home():
            self.controller.show_frame("HomeScreen")    # Takes user back to home screen frame
        def info():
            self.controller.show_frame("UserInfo")  # Takes user to their profile
        
        with open('labels', 'rb') as f:
            dict = pickle.load(f)
            f.close()
        
        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 30
        rawCapture = PiRGBArray(camera, size = (640, 480))

        faceCascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        recogniz = cv2.face.LBPHFaceRecognizer_create()
        recogniz.read("trainer.yml")
        _exit = True
        for frame in camera.capture_continuous(rawCapture, format = "bgr", use_video_port = True):
            frame = frame.array
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = faceCascade.detectMultiScale(
                gray, 
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(300,300),
            )

            for (x,y,w,h) in faces:
                cv2.rectangle(frame, (x,y), (x+w, y+h), (0,255,0), 2)
                _, confidence = recogniz.predict(gray[y:y+h, x:x+w])
                for name, value in dict.items():
                    if value == _id:
                        print(name)
                        print(str(confidence))
                        if i == 6:
                            self.controller.after(400, denied)
                            cv2.destroyAllWindows()
                            self.controller.after(6000, home)
                            _exit = False
                            break
                        if confidence <= 40:
                            print("Welcome" + name)
                            self.controller.after(100, accept)
                            self.controller.after(2000, info)
                            cv2.destroyAllWindows()
                            _exit = False
                            break
                        else:
                            i+=1
                break   # Used to break loop and properly close PiCamera

            cv2.imshow('frame', frame)
            key = cv2.waitKey(1)
            rawCapture.truncate(0)
            if _exit == False:
                break
            if key == 27:
                break
        print("Closeing camera")
        cv2.destroyAllWindows()
        camera.close()
    
    self.controller.after(2000, take, i, _id)

class FaceRecognition(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        # Dictionary used to hold information that can be used in other frames
        self.data = {
                "userID": tk.StringVar(),
                "username": tk.StringVar(),
                "passcode": tk.StringVar(),
                "new_username": tk.StringVar(),
                "new_passcode": tk.StringVar(),
                "start_user": tk.StringVar(),
                "start_pass": tk.StringVar(),
                "re_enter_pass": tk.StringVar(),
                "new_user": tk.StringVar(),
                "new_pass" :tk.StringVar(),
                "admin_pass": tk.StringVar(),
                "edit_user": tk.StringVar(),
                "edit_pass": tk.StringVar(),
                "external_pass": tk.StringVar(),
                "uc_passcode": tk.StringVar()
        }

        container = tk.Frame(self)
        container.pack(side = "top", fill = "both", expand = True)
        container.grid_rowconfigure(0, weight = 1)
        container.grid_columnconfigure(0, weight = 1)

        self.frames = {}
        # A list of the frames that are created
        for F in (FirstOn, StartUp, NewFaceScan, HomeScreen, Profiles, External_Keypad, NewUser, Admin, ReturnUser, 
                External_Profile, UserConfirmation, StartKeypad, Re_EnterKey, AdminKey, Re_Enter_Admin, UserInfo, 
                EditAdminKey ,Re_Enter_EditAdminKey, Error, Error2, AdminError, Query, Successful, Denied, Display,
                EditAdminError,DeleteAdminKey, Confirm_DeleteAdminKey, DeleteAdminError, ProfileDenied, ProfileAccepted,
                UserConfirm_Keypad, UserConfirm_Access, UserConfirm_Denied, Successful_Keypad, Denied_Keypad):
            page_name = F.__name__
            frame = F(parent = container, controller = self)
            self.frames[page_name] = frame 

            # put all of pages in same location;
            # the one on top of stacking order will be visible
            frame.grid(row = 0, column = 0, sticky = "nsew")

        filename = 'database.db'
        # Will create the db file if there is no file named database.db
        if not isfile(filename):
            db = sqlite3.connect(file)
            c = db.cursor()

            # create the columns of the table (id, username, passcode, database ID)
            c.execute("""CREATE TABLE info(
                id integer PRIMARY KEY,
                username text,
                passcode text
            )""")

            db.commit()
            db.close()

        db = sqlite3.connect(file)
        c = db.cursor()
        c.execute("SELECT *, oid FROM info")

        # If there is no information in the db file, go the first on frame, if not then home screen
        records = c.fetchall()
        if not records:
            self.show_frame("FirstOn")
            #self.after(100, speak_start, self)  #Lack of power, commented out for final presentation
        else:
            self.show_frame("HomeScreen")

        db.commit()
        db.close()

    # How we can switch to other frames, using self.controller.show_frame("frame_name") 
    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()

# frame when the system is booted for first time 
class FirstOn(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')
        label = tk.Label(self, text = "Welcome to the Facial Recognition Lock System]\n As a New User\n Please Press the Button Below to Get Started!",
                font = "Arial 30", width = 50, height = 4, fg = "yellow", bg = "teal")
        label.pack(side = "top", pady = 90)

        button = tk.Button(self, text = "Continue", font = "Arial 18", command = lambda: controller.show_frame("StartUp"))
        button.pack(side = "bottom", pady = 90)

# frame to enter information for new admin
class StartUp(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        name_label = tk.Label(self, text = "Enter Your Name", font = "Arial 18", bg = 'teal', fg = 'yellow')
        name_label.place(x = 250, y = 100)
        pass_label = tk.Label(self, text = "Please Enter Passcode\nvia Keypad or Entry Box\nUsing 0-9 and A-D", font = "Arial 18", bg = 'teal', fg = 'yellow')
        pass_label.place(x = 250, y = 190)
        re_en = tk.Label(self, text = "Re-Enter Passcode", font = "Arial 18", bg = "teal", fg = "yellow")
        re_en.place(x = 250, y = 330)

        self.name = tk.Entry(self, textvariable = self.controller.data["start_user"], font = "Arial 18")
        self.name.place(x=550, y = 100)
        self.passcode = tk.Entry(self, textvariable = self.controller.data["start_pass"], font = "Arial 18", show = "*")
        self.passcode.place(x=550, y=200)
        self.re_enter = tk.Entry(self, textvariable = self.controller.data["re_enter_pass"], font = "Arial 18", show = "*")
        self.re_enter.place(x=550, y = 320)

        submit = tk.Button(self, text = "Submit", command = lambda: self.submit(), font = "Arial 18")
        submit.place(x = 250, y = 440)

        keypad = tk.Button(self, text = "Keypad", command = lambda: [controller.show_frame("StartKeypad")], font = "Arial 18")
        keypad.place(x=450, y = 440)

        clear_but = tk.Button(self, text = "Clear Entries", font = "Arial 18", command = lambda: self.clear())
        clear_but.place(x = 650, y = 440)

    # Function to enter in the information into the database
    def submit(self):
        with sqlite3.connect(file) as db:
            c = db.cursor()

        global USERNAME
        
        USERNAME = ""
        USERNAME = self.controller.data["start_user"].get()
        name = self.controller.data["start_user"].get()
        passcode = self.controller.data["start_pass"].get()
        check = self.controller.data["re_enter_pass"].get()

        if (passcode == check):
            c.execute("INSERT INTO info (username, passcode) VALUES(?, ?)", (name, passcode))

            db.commit()
            db.close()

            self.name.delete(0, tk.END)
            self.passcode.delete(0, tk.END)
            self.re_enter.delete(0, tk.END)

            self.controller.show_frame("NewFaceScan")   # Goes to face scan frame where user will be prompted to press on button

        else:
            messagebox.showerror("Error","Incorrect Passcode\nPlease Try Again")
            self.passcode.delete(0, tk.END)
            self.re_enter.delete(0, tk.END)

    def clear(self):
        self.name.delete(0, tk.END)
        self.passcode.delete(0, tk.END)
        self.re_enter.delete(0, tk.END)

class NewFaceScan(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        label = tk.Label(self, text = "Account Facial Scan", font = "Arial 30", bg = "teal", fg = "yellow", height = 2)
        label.pack(side = "top", pady = 5)

        # Will create a continue button, and will call the capture function to get user's pictures
        scan = tk.Button(self, text = "Face Scan", font = "Arial 22", command = lambda: [self.create(), self.capture()])
        scan.place(x=410, y = 330)

    def bye(self):
        self.cont.destroy()
        
    def create(self):
        self.cont = tk.Button(self, text = "Continue", font = "Arial 18", command = lambda: [self.controller.show_frame("HomeScreen"), train(self), self.bye()])
        self.cont.pack(side = "bottom", pady = 20)
    
    def label(self):
        still = tk.Label(self, text = "Please wait for camera preview to show up", font = "Arial 25", bg = "teal", fg = "yellow")
        still.place(x= 120, y = 200)

    def capture(self):
        self.after(200, self.label)
        global USERNAME
        global ID
        ID = ""
        with sqlite3.connect(file) as db:
            c = db.cursor()
        c.execute("SELECT * FROM info ORDER BY id DESC LIMIT 1")
        result = c.fetchone()
        # Will get the ID of the recently added user
        ID = result[0]
        db.commit()
        db.close()
        # capture function being called
        cap(self, USERNAME, ID)

class HomeScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')
        
        label = tk.Label(self, text = "Home Screen", font = "Arial 45", bg = "teal", fg = "yellow")
        label.pack(side = "top", pady = 50)

        # takes user to profile frame
        SignIn = tk.Button(self, text = "Profiles", font = "Arial 30", fg = "yellow", bg = "green", command = lambda: self.controller.show_frame("Profiles"))
        SignIn.place(x=200, y = 200)

        # takes user to passcode frame where user will user external keypad
        Create = tk.Button(self, text = "User Passcode", font = "Arial 30", fg = 'yellow', bg = 'green', command = lambda: self.controller.show_frame("External_Profile"))
        Create.place(x=600, y=200)

        # will call recognize funtion to automatically go through the trainer and pick the closest user, with a good confidence level
        scan = tk.Button(self, text = "Face Scan", font = "Arial 30", fg = "yellow", bg = "green", command = lambda:[self.controller.show_frame("Display"), self.aquire()])
        scan.place(x=390, y=300)
        
        _exit = tk.Button(self, text = "Exit", font = "Arial 30", fg = "yellow", bg = "green", command = lambda: self.exit())
        _exit.pack(side = "bottom", pady = 100)
        
    def aquire(self):
        self.after(500, recognize, self, 0)
    
    def exit(self):
        self.controller.destroy()

class External_Profile(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.parent = parent
        self.configure(background = 'teal')

        # can select user who wants to access lock
        label = tk.Label(self, text = "Who Wants to Access Lock?", font = "Arial 35 bold", bg= "teal", fg = "yellow", height = 1)
        label.pack(side = "top", pady = 10)

        back = tk.Button(self, text = "Back", font = "Arial 20", height = 2, width = 15, bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("HomeScreen"))
        back.pack(side = "bottom", pady = 30)

        user = tk.Label(self, text = "Username", font = "Arial 30", bg = "teal", fg = "yellow")
        user.place(x=50, y = 100)

        bigfont = font.Font(family = "Helvetica", size = 30)
        self.parent.option_add("*TCombobox*Listbox*Font", bigfont)
        self.list = ttk.Combobox(self, width = 30, height = 200, postcommand = self.update_list, font = "Arial 30")
        self.list.place(x = 250, y = 100)
        #self.list.current()
        self.list.bind("<<ComboboxSelected>>", self.call_back)
    
    def update_list(self):
        lst = []
        lst = self.getList()
        self.list['values'] = lst

    # Will allow for the dropbox list to automatically update when new users are added
    def getList(self):
        with sqlite3.connect(file) as db:
            c = db.cursor()

        c.execute("SELECT *, oid FROM info")
        records = c.fetchall()
        items = []
        for record in records:
            items.append(record[1])
        db.close()
        return items

    # Will call the external kepad frame
    def call_back(self, event):
        self.list.SelectedIndex = -1
        global USERNAME
        USERNAME = ""
        USERNAME = self.list.get()
        self.controller.show_frame("External_Keypad")
        self.list.set('')

class External_Keypad(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        main_label = tk.Label(self, text = "External Keypad", bg = 'teal', fg = 'yellow', font = "Arial 35")
        main_label.pack(side = "top", pady = 10)

        # When user presses button, will call a thread that will read keypresses from keypad
        # so that the keypresses can be shown in entry label, so show that each keypress is entered
        user_lab = tk.Label(self, text = "Please press the 'Use External Keypad'\nbutton below to use\nExternal Keypad", bg = 'teal', fg = 'yellow', font = "Arial 20")
        user_lab.place(x=10, y = 100)

        key_button = tk.Button(self, text = "Use External Keypad", bg = "green", fg = "yellow", font = "Arial 30", command = lambda: self.thread())
        key_button.pack(side = "bottom", pady = 90)

        self.label = tk.Entry(self, textvariable = self.controller.data["external_pass"], font = "Arial 25", show = "*")
        self.label.place(x = 150, y = 300)
    
    # Thread that will call the keypad function
    def thread(self):
        self.t1 = threading.Thread(target = self.Keypad)
        if not self.t1.is_alive():
            try:
                self.t1.start()
                self.controller.after(100, self.read_queue)
            except RuntimeError:
                self.t1 = threading.Thread(target= self.Keypad)
                self.t1.start()
        self.t1.join()

    # Will read the last value put into the queue from the keypad function
    # So that the entry label can be updated with that key
    def read_queue(self):
        if q.empty():
            self.controller.after(100, self.read_queue)
        else:
            val = q.get(0)
            self.label.insert('end', val)
            self.controller.after(100, self.read_queue)
    
    def Keypad(self):
        def accept(self):
            self.controller.show_frame("Successful_Keypad")
            GPIO.output(18, GPIO.HIGH)
            #self.controller.after(100, accept_thread(self))
        
        # # not enough power in design to support this

        # def accept_thread(self):
        #     t1 = threading.Thread(target = speak_accept, args=(self,))
        #     t1.start()
        #     t1.join()
        
        # def denied_thread(self):
        #     t2 = threading.Thread(target=speak_denied, args=(self,))
        #     t2.start()
        #     t2.join() 
        
        def denied(self):
            self.controller.show_frame("Denied_Keypad")
            #self.controller.after(100, denied_thread(self))
        
        def home(self):
            self.controller.show_frame("HomeScreen")
            GPIO.output(18, GPIO.LOW)
            self.controller.after(1000, end, self)
        # Set gpio pins
        GPIO.setwarnings(False)
        ROW_PINS = [5,6,13,19]
        COL_PINS = [12,16,20,21]

        factory = rpi_gpio.KeypadFactory()
        keypad = factory.create_keypad(keypad = KEYPAD, row_pins = ROW_PINS, col_pins = COL_PINS)
        def keyPress(key):
            code = self.controller.data["external_pass"].get()
            global tries
            global inp
            global USERNAME
            if (key == '*'):
                inp = ""
                with q.mutex:
                    q.queue.clear()
                    self.label.delete(0, tk.END)
            elif (key == "#"):
                if tries == 3:
                    self.label.delete(0, tk.END)
                    self.controller.after(100, denied(self))
                    self.controller.after(7000, home(self))
                    tries = 0
                    inp = ""
                    keypad.cleanup()
                    with q.mutex:
                        q.queue.clear()

                with sqlite3.connect(file) as db:
                    c = db.cursor()
                # Get passcode of specific user
                c.execute('''SELECT * FROM info WHERE username = ?''', (USERNAME,))
                results = c.fetchall()
                #variable to fetch passcode of user
                u_pass = ""
                for i in results:
                    u_pass = i[2]   # get passcode from table (id, username, passcode, database ID)
                if code == u_pass:
                    self.label.delete(0, tk.END)
                    self.controller.after(100, accept(self))
                    self.controller.after(7000, home(self))
                    inp = ""
                    tries = 0
                    keypad.cleanup()
                    # Will clear queue
                    with q.mutex:
                        q.queue.clear()
                else:
                    self.label.delete(0, tk.END)
                    tries += 1
                    inp = ""
                    with q.mutex:
                        q.queue.clear()
            else:
                inp = inp + key
                # puts keypress into queue so that it can be read 
                q.put(key)
        keypad.registerKeyPressHandler(keyPress)

class Profiles(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        info = tk.Label(self, text = "Choose a way to Access Profile Information", font = "Arial 30", bg = 'teal', fg = "yellow", height = 2)
        info.place(x = 130, y = 30)

        returning = tk.Button(self, text = "Returning User", font = "Arial 20", height = 3, bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("ReturnUser"))
        returning.place(x = 200, y = 200)

        check = tk.Button(self, text = "Admin Page", font = "Arial 20", height = 3, width = 13, bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("AdminKey"))
        check.place(x = 600, y = 200)

        back = tk.Button(self, text = "Back", font = "Arial 20", height = 2, width = 15, bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("HomeScreen"))
        back.pack(side = "bottom", pady = 30)

class NewUser(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        label = tk.Label(self, text = "New User", font = "Arial 35", bg = "teal", fg = "Yellow", height = 2, width = 20)
        label.pack(side = "top", pady = 2)

        name = tk.Label(self, text = "Input Name", font = "Arial 20", bg = "light green", fg = "black", height = 2, width = 15)
        name.place(x = 100, y = 120)

        passcode = tk.Label(self, text = "Input Passcode", font = "Arial 20", bg = "light green", fg = "black", height = 2, width = 15)
        passcode.place(x = 100, y = 220)

        re_in_passcode = tk.Label(self, text = "Re-Enter Passcode", font = "Arial 20", bg = "light green", fg = "black", height = 2, width = 15)
        re_in_passcode.place(x = 100, y = 320)

        # entry boxes
        self.in_name = tk.Entry(self, textvariable = self.controller.data["new_user"], font = "Arial 40", width = 20)
        self.in_name.place(x = 400, y = 120)

        self.in_pass = tk.Entry(self, textvariable = self.controller.data["new_pass"], font = "Arial 40", width = 20, show = "*")
        self.in_pass.place(x = 400, y = 220)

        self.re_in_pass = tk.Entry(self, textvariable = self.controller.data["re_enter_pass"], font = "Arial 40", width = 20, show = "*")
        self.re_in_pass.place(x = 400, y = 320)

        back = tk.Button(self, text = "Back", font = "Arial 20", bg = "yellow", fg = "black", width = 15, height = 1, command = lambda: [self.controller.show_frame("Profiles"), self.clear()])
        back.place(x = 600, y = 500)

        next_frame = tk.Button(self, text = "Facial Scan", font = "Arial 20", bg = "yellow", fg = "black", width = 15, height = 1, command = lambda: self.enter())
        next_frame.place(x = 200, y = 500)

    def clear(self):
        self.in_name.delete('0', tk.END)
        self.in_pass.delete('0', tk.END)
        self.re_in_pass.delete('0', tk.END)

    def enter(self):
        global USERNAME
        global ID
        ID = ""
        USERNAME = ""
        USERNAME = self.controller.data["new_user"].get()
        username = self.controller.data["new_user"].get()
        passcode = self.controller.data["new_pass"].get()
        re_enter = self.controller.data["re_enter_pass"].get()

        if (passcode == re_enter):
            with sqlite3.connect(file) as db:
                c = db.cursor()

            # Inserts information into database
            c.execute("INSERT INTO info (username, passcode) VALUES(?, ?)", (username, passcode))
            c.execute("SELECT * FROM info ORDER BY id DESC LIMIT 1")
            result = c.fetchone()
            ID = result[0]

            db.commit()
            db.close()

            self.in_name.delete(0, tk.END)
            self.in_pass.delete(0, tk.END)
            self.re_in_pass.delete(0, tk.END)

            self.controller.show_frame("NewFaceScan")
        else:
            self.controller.show_frame("Error2")
            self.in_name.delete(0, tk.END)
            self.in_pass.delete(0, tk.END)
            self.re_in_pass.delete(0, tk.END)

class UserConfirmation(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        label = tk.Label(self, text = "User Confirmation", font = "Arial 35", bg = 'teal', fg = "yellow")
        label.pack(side = "top", pady = 10)

        profile_scan = tk.Button(self, text = "Face Scan to\naccess profile", font = "Arial 20", width = 15, height = 3, bg = "yellow", fg = "black", command = lambda: [self.controller.show_frame("Display"), self.prof()])
        profile_scan.place(x=200, y = 250)

        scan = tk.Button(self, text = "Face Scan to access Door", font = "Arial 20", width = 20, height = 3, bg = "yellow", fg = "black", command = lambda: [self.controller.show_frame("Display"), self.action()])
        scan.pack(side = "bottom", pady = 60)

        passcode = tk.Button(self, text = "User Passcode\nto access profile", font = "Arial 20", bg = "yellow", fg = "black", width = 15, height = 3, command = lambda: self.controller.show_frame("UserConfirm_Keypad"))
        passcode.place(x = 600, y = 250)
        
    def prof(self):
        global USERNAME
        with sqlite3.connect(file) as db:
            c = db.cursor()
        # gets username of the user that wants to access their profile
        c.execute('''SELECT * FROM info WHERE username = ?''', (USERNAME,))
        record = c.fetchall()
        for r in record:
            _id = r[0]
        
        # calls the scap_profile function to scan user's face
        self.after(500, scan_profile, self, 0, _id)

    def action(self):
        global USERNAME
        with sqlite3.connect('database.db') as db:
            c = db.cursor()
        # Get username of the user that wants to access door
        c.execute('''SELECT * FROM info WHERE username = ?''' ,(USERNAME,))
        record = c.fetchall()
        for r in record:
            u_id = r[0]
        
        # Scan user to access door directly
        self.after(500, scan, self, 0, u_id)

class UserInfo(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        label = tk.Label(self, text = "User Profile", bg = "teal", font = "Arial 40 bold", fg = "yellow", height = 2)
        label.pack(side = 'top', pady = 10)

        change_pass = tk.Button(self, text = "Change Passcode", bg = 'yellow', fg = 'black', height = 3, font = "Arial 25", command = lambda: self.user_pass())
        change_pass.place(x=100, y = 150)

        delete = tk.Button(self, text = "Delete User Profile", bg = 'yellow', fg = 'black', height = 3, font = "Arial 25", command = lambda: self.delete_user())
        delete.place(x=550, y = 150)

        home = tk.Button(self, text = "Back to Home Screen", bg = 'yellow', fg = 'black', height = 3, font = "Arial 25", command = lambda: self.controller.show_frame("HomeScreen"))
        home.pack(side = 'bottom', pady = 60)

    # Get a frame to pop up so the user can change information
    def user_pass(self):
        global root
        root = tk.Tk()
        root.title("Change User Passcode")
        root.geometry("900x500")
        root.configure(background = 'teal')

        global USERNAME
        global ID
        ID = ""
        
        with sqlite3.connect(file) as db:
            c = db.cursor()
        
        # Allows the information of the user to be shown
        c.execute("SELECT * FROM info WHERE username = ?", (USERNAME,))
        results = c.fetchall()

        title = tk.Label(root, text = "Edit User Information", font = "Arial 35", bg = "teal", fg = "yellow", width = 22, height = 2)
        title.pack(side = "top")

        u_name = tk.Label(root, text = "Edit User's name", font = "Arial 16", bg = 'light green', fg = 'black')
        u_name.place(x=100, y = 150)

        p_code = tk.Label(root, text = "Edit User's Passcode", font = "Arial 16", bg = "light green", fg = "black")
        p_code.place(x=100, y = 300)

        self.u_name_edit = tk.Entry(root, font = "Arial 20")
        self.u_name_edit.place(x=400, y=150)

        self.p_code_edit = tk.Entry(root, font = "Arial 20")
        self.p_code_edit.place(x = 400, y = 300)

        but = tk.Button(root, text = "Update Information", font = "Arial 20", bg = "yellow", fg = "black", command = lambda: self.update())
        but.pack(side = "bottom", pady = 20)

        db.close()

        # insert the information into the entry labels
        for r in results:
            ID = r[0]
            self.u_name_edit.insert(0, r[1])
            self.p_code_edit.insert(0, r[2])
    
    # changes the information in the database
    def update(self):
        name = ""
        passcode = ""
        name = self.u_name_edit.get()
        passcode = self.p_code_edit.get()
        global ID

        print(name, passcode)
        message = messagebox.askquestion('Update', "Are you sure you want to change information?")

        with sqlite3.connect(file) as db:
                c = db.cursor()
        if message == 'yes':
            # Checks to see if it is not admin id number
            if int(ID) != 1:
            # Changes the info in the database for the user
                c.execute("UPDATE info SET username = ?, passcode = ? WHERE id = ?", (name, passcode, int(ID)))

                db.commit()
                db.close()
                root.destroy()
            else:
                # Shows an error message if it is admin
                messagebox.showerror("Profile Error!", "Admin cannot change information")
                self.controller.show_frame("HomeScreen")
        if message == 'no':
            self.controller.show_frame("UserInfo")
            root.destroy()

    # Allows user to delete entire profile
    def delete_user(self):
        global USERNAME
        global ID
        ID = ""

        with sqlite3.connect(file) as db:
            c = db.cursor()
        
        c.execute("SELECT * FROM info WHERE username = ?", (USERNAME,))
        result = c.fetchall()
        for r in result:
            ID = r[0]
        
        q = messagebox.askquestion("Delete Profile", "Delete User Profile?")

        if q == 'yes':
            # Checks to see if it is not the admin wanting to delete their profile
            if int(ID) != 1:
                # Deletes all info from the database
                c.execute("DELETE FROM info WHERE id=?", ID)
                db.commit()
                db.close()
                self.controller.show_frame("HomeScreen")
            else:
                # Error shown if it is the admin  that wants to delete their profile
                messagebox.showerror("Profile Error", "Cannot delete Admin Profile")
                self.controller.show_frame("HomeScreen")
        if q == 'no':
            self.controller.show_frame("UserInfo")
            
# Admin page where we can add a new user, or see the users in the database
class Admin(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        admin = tk.Label(self, text = "Welcome Admin", bg = "teal", font = "Arial 40 bold", fg = "yellow", height = 2)
        admin.place(x = 350, y = 30)
        
        new_user = tk.Button(self, text = "New User", font = "Arial 20", height = 3, width = 13, bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("NewUser"))
        new_user.place(x = 200, y = 200)

        info = tk.Button(self, text = "Show Users in Database", font = "Arial 20", height = 3, width = 20, bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("Query"))
        info.place(x=500, y = 200)

        home = tk.Button(self, text = "Go to Home Screen", font = "Arial 20", bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("HomeScreen"))
        home.pack(side = "bottom", pady = 70)

# Frame to select the user that wants to access profile/lock
class ReturnUser(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller 
        self.parent = parent
        self.configure(background = "teal")

        label = tk.Label(self, text = "Returning User", font = "Arial 35 bold", bg = 'teal', fg = "yellow", height = 1)
        label.place(x = 350, y = 10)

        back = tk.Button(self, text = "Back", font = "Arial 20", height = 2, width = 15, bg = "yellow", fg = "black", command = lambda: self.controller.show_frame("Profiles"))
        back.pack(side = "bottom", pady = 30)

        user = tk.Label(self, text = "Username", font = "Arial 30", bg = "teal", fg = "yellow")
        user.place(x = 50, y = 100)

        bigfont = font.Font(family = "Helvetica", size = 30)
        self.parent.option_add("*TCombobox*Listbox*Font", bigfont)
        self.list = ttk.Combobox(self, width = 30, height = 200, postcommand = self.update_list, font = "Arial 30")
        self.list.place(x = 250, y = 100)

        self.list.bind("<<ComboboxSelected>>", self.call_back)

    # Updates the list to show all users in the database
    def update_list(self):
        lst = []
        lst = self.getList()
        self.list['values'] = lst
    
    # Get's info from the database
    def getList(self):
        with sqlite3.connect('database.db') as db:
            c = db.cursor()

        c.execute("SELECT *, oid FROM info")
        records = c.fetchall()
        items = []
        for record in records:
            items.append(record[1])
        db.close()
        return items
    # Will go to user confirmation frame
    def call_back(self,event):
        self.list.SelectedIndex = -1
        global USERNAME
        USERNAME = ""
        USERNAME = self.list.get()
        self.controller.show_frame("UserConfirmation")
        print(USERNAME)
        self.list.set('')

class Query(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        main = tk.Label(self, text = "User Information", font = "Arial 35", bg = "teal", fg = "yellow", height = 1)
        main.place(x=350, y = 10)

        name = tk.Label(self, text = "Enter the UserID in the\nbox above to either edit\n or delete the user", font = "Arial 20", bg = 'light green', fg = 'black')
        name.place(x=30, y = 300)

        self.entry = tk.Entry(self, textvariable = self.controller.data["userID"], font = "Arial 18")
        self.entry.place(x=30, y = 264)

        but1 = tk.Button(self, text = "Edit User Information", font = "Arial 20", bg = "yellow", fg = "black", command = lambda: self.edit())
        but1.place(x=30, y = 530)

        but2 = tk.Button(self, text = "Delete User Information", font = "Arial 20", bg = "yellow", fg = "black", command = lambda: self.delete())
        but2.place(x=330, y = 530)

        but3 = tk.Button(self, text = "Update User Information", font = "Arial 20", bg = "yellow", fg = "black", command = lambda: self.show())
        but3.place(x=670, y = 530)
        
        home = tk.Button(self, text = "Go back", font = "Arial 20", bg = "yellow", fg = "black", command= lambda: self.controller.show_frame("Admin"))
        home.place(x=30, y = 30)

    def show(self):
        # go through database and print info
        with sqlite3.connect(file) as db:
            c = db.cursor()

        c.execute("SELECT *, oid FROM info")
        records = c.fetchall()

        #Loop through results
        print_records = ''
        print_records+= "UserID\t              Username \t            DatabaseID\n"
        print_records+="----------------------------------------------------------------------\n"

        for record in records:
            print_records += str(record[0]) +" \t| " + str(record[1]) + " \t| " + str(record[3]) + "\n"

        db.commit()
        db.close()

        query_label = tk.Label(self, text = print_records, bg = "teal", fg = "yellow",font = "Arial 16")
        query_label.place(x = 450, y = 100)

    # Allows user to delete user and profile from database
    def delete(self):
        global ID
        global USERNAME
        USERNAME = ""
        ID = ""
        ID = self.controller.data["userID"].get()
        with sqlite3.connect('database.db') as db:
            c = db.cursor()
        c.execute("SELECT * FROM info WHERE id = " + ID)
        records = c.fetchall()
        print(records)
        for r in records:
            USERNAME = r[1]
            _id = r[0]
            print(USERNAME)
        result = messagebox.askquestion("Delete User", "Are You Sure You Want\n To Delete This User?", icon= "warning")

        if result == 'yes':
            ## Checks whether it is admin that wants to delete profile
            if int(_id) != 1:
                self.controller.show_frame("DeleteAdminKey")
                self.entry.delete('0', 'end')
            else:
                messagebox.showerror("ERROR!", "Cannot Delete Admin Information!")
        if result == 'no':
            self.entry.delete('0', 'end')

    # allows us to manipulate the user's passcode info by changing it
    def edit(self):
        global root
        root = tk.Tk()
        root.title("Edit User Information")
        root.geometry("1000x500")
        root.configure(background = 'teal')

        global ID

        with sqlite3.connect(file) as db:
            c = db.cursor()

        record_id=self.controller.data["userID"].get()
        ID = self.controller.data["userID"].get()

        c.execute("SELECT * FROM info WHERE id = " + record_id)
        records = c.fetchall()

        title = tk.Label(root, text = "Edit User Information", font = "Arial 35", bg = "teal", fg = "yellow", width = 22, height = 2)
        title.pack(side = "top")

        u_name = tk.Label(root, text = "Edit User's name", font = "Arial 16", bg = 'light green', fg = 'black')
        u_name.place(x=100, y = 150)

        p_code = tk.Label(root, text = "Edit User's Passcode", font = "Arial 16", bg = "light green", fg = "black")
        p_code.place(x=100, y = 300)

        self.u_name_edit = tk.Entry(root, font = "Arial 20")
        self.u_name_edit.place(x=400, y=150)

        self.p_code_edit = tk.Entry(root, font = "Arial 20")
        self.p_code_edit.place(x = 400, y = 300)

        but = tk.Button(root, text = "Update Information", font = "Arial 20", bg = "yellow", fg = "black", command = lambda: self.update())
        but.pack(side = "bottom", pady = 20)

        for record in records:
            self.u_name_edit.insert(0, record[1])
            self.p_code_edit.insert(0, record[2])

    # Promp user if they want to change passcode, will require admin's passcode
    def update(self):
        global USERNAME
        global PASSCODE
        global ID

        # set info to global vaiables to use in other frames
        USERNAME = self.u_name_edit.get()   
        PASSCODE = self.p_code_edit.get()

        message = messagebox.askquestion("Update", "Are You Sure You Want to\nUpdate User Information?")

        if message == 'yes':
            # Checks whether the admin themselves is wanting to change their own information
            if int(ID) != 1:
                # go to virtual keypad to ask for admin passcode
                self.controller.show_frame("EditAdminKey")
                root.destroy()
                self.entry.delete('0', 'end')
            else:
                messagebox.showerror("ERROR!", "Cannot Edit Admin Information, going back to Home Screen!")
                root.destroy()
                self.entry.delete('0', tk.END)
                self.controller.show_frame("HomeScreen")
        else:
            self.controller.show_frame("Query")
            self.entry.delete('0', 'end')

# a frame that will pop up when the user uses the facial recognition
class Display(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')
        
        label = tk.Label(self, text = "Please Stay Still \nto get Face Scanned", bg = 'teal', fg = 'yellow', font = "Arial 30")
        label.pack()

# Virtual keypad when the system is turned on
class StartKeypad(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        self.start_key = tk.Entry(self, textvariable = self.controller.data["start_pass"], font = "Arial 18", show = "*")
        self.start_key.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        label = tk.Label(self, text = "Please Enter Passcode\nUse # to Enter", font = "Arial 20", bg = "teal", fg = "yellow")
        label.grid(row = 3, column = 80)

        # create keypad
        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.disp(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def disp(self, val):
        global PIN

        if val == '*':
            self.start_key.delete('0', 'end')
            PIN = ""
            self.start_key.insert('end', PIN)

        elif val == "#":
            self.controller.show_frame("Re_EnterKey")
            PIN = ""
        else:
            PIN += val
            self.start_key.insert('end', val)

# Re-enter the passcode they entered
class Re_EnterKey(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        label = tk.Label(self, text = "Please Re-Enter Passcode\nUse # to Enter", font = "Arial 18", bg = "teal", fg = "yellow")
        label.grid(row = 2, column = 1)

        self.start_keyp = tk.Entry(self, textvariable = self.controller.data["re_enter_pass"], font = "Arial 18", show = "*")
        self.start_keyp.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        # create keypad
        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.display(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def display(self, val):
        global PIN
        global ID
        global USERNAME
        
        USERNAME = ""
        ID = ""
        
        USERNAME = self.controller.data["start_user"].get()
        new_user = self.controller.data["start_user"].get()
        new_pass = self.controller.data["start_pass"].get()
        re_enter = self.controller.data["re_enter_pass"].get()

        if val == '*':
            #PIN = PIN[:-1]
            self.start_keyp.delete('0', 'end')
            PIN = ""
            self.start_keyp.insert('end', PIN)

        elif val == "#":
            if(new_pass == re_enter):
                with sqlite3.connect(file) as db:
                    c = db.cursor()

                # inserts the information into the database
                c.execute("INSERT INTO info (username, passcode) VALUES(?, ?)", (new_user, new_pass))
                c.execute("SELECT * FROM info ORDER BY id DESC LIMIT 1")
                result = c.fetchone()
                ID = result[0]
                print(ID)

                db.commit()
                db.close()
                # goes to frame where system will prompt user to have their pictures taken
                self.controller.show_frame("NewFaceScan")
                self.start_keyp.delete('0', 'end')
            else:
                self.controller.show_frame("Error")
                self.start_keyp.delete('0', 'end')
            PIN = ""
        else:
            PIN += val
            self.start_keyp.insert('end', val)

# Virtual keypad for admin passcode
class AdminKey(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        self.start_key = tk.Entry(self, text = "", font = "Arial 18", show = "*")
        self.start_key.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        label = tk.Label(self, text = "Please Enter Passcode\nUse # to Enter", font = "Arial 20", bg = "teal", fg = "yellow")
        label.grid(row = 3, column = 80)

        # create keypad
        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.dis(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def dis(self, val):
        global PIN

        if val == '*':
            self.start_key.delete('0', 'end')
            PIN = ""
            self.start_key.insert('end', PIN)

        elif val == "#":
            self.controller.show_frame("Re_Enter_Admin")
            PIN = ""
            self.start_key.delete('0', 'end')
        else:
            PIN += val
            self.start_key.insert('end', val)

# Virtual keypad to re-enter the admin passcode
class Re_Enter_Admin(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        label = tk.Label(self, text = "Please Re-Enter Passcode\nUse # to Enter", font = "Arial 18", bg = "teal", fg = "yellow")
        label.grid(row = 2, column = 1)

        self.s_key = tk.Entry(self, textvariable = self.controller.data["re_enter_pass"], font = "Arial 18", show = "*")
        self.s_key.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        # create keypad
        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.display(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def display(self, val):
        global PIN

        userID = 1
        re_enter = self.controller.data["re_enter_pass"].get()

        with sqlite3.connect(file) as db:
            c = db.cursor()

        # acquires the admin's information
        db_query = ("SELECT * FROM info WHERE id = ?")
        c.execute(db_query, [(userID)])

        results = c.fetchall()

        if val == "*":
            self.s_key.delete('0', 'end')
            PIN = ""
            self.s_key.insert('end', PIN)
        elif val == "#":
            if results:
                for i in results:
                    if(i[2] == re_enter):
                        self.controller.show_frame("Admin")
                        self.s_key.delete('0', 'end')
                    else:
                        self.controller.show_frame("AdminError")
                        self.s_key.delete('0', 'end')
            PIN = ""
        else:
            PIN += val
            self.s_key.insert('end', val)

# Frame to ask admin for passcode when deleting a user from admin mode
class DeleteAdminKey(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        self.A_key = tk.Entry(self, text = "", font = "Arial 18", show = "*")
        self.A_key.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        label = tk.Label(self, text = "Please Enter Passcode\nUse # to Enter", font = "Arial 20", bg = "teal", fg = "yellow")
        label.grid(row = 3, column = 80)

        # create keypad
        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.DISP(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def DISP(self, val):
        global PIN
        PIN = ""

        if val == '*':
            self.A_key.delete('0', 'end')
            PIN = ""
            self.A_key.insert('end', PIN)

        elif val == "#":
            self.controller.show_frame("Confirm_DeleteAdminKey")
            PIN = ""
        else:
            PIN += val
            self.A_key.insert('end', val)

# re-enter passcode for admin mode to delete specific user
class Confirm_DeleteAdminKey(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        label = tk.Label(self, text = "Please Re-Enter Passcode\nUse # to Enter", font = "Arial 18", bg = "teal", fg = "yellow")
        label.grid(row = 2, column = 1)

        self.C_key = tk.Entry(self, textvariable = self.controller.data["re_enter_pass"], font = "Arial 18", show = "*")
        self.C_key.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        # create keypad
        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.DIS(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def DIS(self, val):
        global ID
        global PIN
        global USERNAME
        _id = 1
        dirname = "./images/" + str(ID) + " " + USERNAME
        
        re_enter = self.controller.data["re_enter_pass"].get()
        with sqlite3.connect(file) as db:
            c = db.cursor()

        db_query = ("SELECT * FROM info WHERE id = ?")
        c.execute(db_query, [(_id)])
        results = c.fetchall()

        if val == "*":
            self.C_key.delete('0', 'end')
            PIN = ""
            self.C_key.insert('end', PIN)
        elif val == "#":
            if results:
                for i in results:
                    if(i[2] == re_enter):
                        if int(ID) != 1:
                            # Will delete all info of user from database
                            c.execute("DELETE FROM info WHERE id =?", ID)
                            self.controller.show_frame("Admin")
                            self.C_key.delete('0', 'end')
                            try:
                                # delete folder of user's images
                                shutil.rmtree(dirname)
                                print(dirname + " deleted")
                            except:
                                print("No directory")
                        else:
                            messagebox.showerror("Profile Error", "Cannot delete Admin Profile from database!")
                    else:
                        self.controller.show_frame("DeleteAdminError")
                        self.C_key.delete('0', 'end')
            PIN = ""
        else:
            PIN += val
            self.C_key.insert('end', val)

        db.commit()
        db.close()

# entering admin passcode to edit user information
class EditAdminKey(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        self.keypad = tk.Entry(self, text = "", font = "Arial 18", show = "*")
        self.keypad.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        label = tk.Label(self, text = "Please Enter Passcode\nUse # to Enter", font = "Arial 20", bg = "teal", fg = "yellow")
        label.grid(row = 3, column = 80)

        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.d_play(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def d_play(self, val):
        global PIN
        if val == "*":
            self.keypad.delete("0", "end")
            PIN = ""
            self.keypad.insert('end', PIN)
        elif val == "#":
            self.controller.show_frame("Re_Enter_EditAdminKey")
            PIN = ""
        else:
            PIN += val
            self.keypad.insert('end', val)

# Re-enter admin passcode to edit user information
class Re_Enter_EditAdminKey(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "teal")

        label = tk.Label(self, text = "Please Re-Enter Passcode\nUse # to Enter", font = "Arial 18", bg = "teal", fg = "yellow")
        label.grid(row = 2, column = 1)

        self.p_key = tk.Entry(self, textvariable = self.controller.data["re_enter_pass"], font = "Arial 18", show = "*")
        self.p_key.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.Display(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def Display(self, val):
        global PIN
        global ID
        global USERNAME
        global PASSCODE

        PIN = ""

        userID = 1
        re_enter = self.controller.data["re_enter_pass"].get()

        with sqlite3.connect(file) as db:
            c = db.cursor()

        db_query = ("SELECT * FROM info WHERE id = ?")
        c.execute(db_query, [(userID)])

        results = c.fetchall()

        if val == "*":
            self.p_key.delete('0', 'end')
            PIN = ""
            self.p_key.insert('end', PIN)
        elif val == "#":
            if results:
                for i in results:
                    if(i[2] == re_enter):
                        # update the information in the database with new information for user
                        c.execute("""UPDATE info SET username = ?, passcode = ? WHERE id=?""",
                                    (USERNAME, PASSCODE, int(ID))
                                    )
                        self.controller.show_frame("Admin")
                        self.p_key.delete('0', 'end')
                    else:
                        self.controller.show_frame("EditAdminError")
                        self.p_key.delete('0', 'end')
            PIN = ""
        else:
            PIN += val
            self.p_key.insert('end', val)
        db.commit()
        db.close()

# virtual keypad to enter user passcode to confirm identity
class UserConfirm_Keypad(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'teal')

        self.uc_key = tk.Entry(self, textvariable = self.controller.data["uc_passcode"], font = "Arial 18", show = "*")
        self.uc_key.grid(row = 100, column = 200, columnspan = 30, padx = 10, pady = 1)

        label = tk.Label(self, text = "Please Enter Passcode", font = "Arial 18", bg = 'teal', fg = 'yellow')
        label.grid(row = 2, column = 1)

        for y, row in enumerate(keys, 1):
            for x, key in enumerate(row):
                buttons = tk.Button(self, text = key, font = "Arial 22", width = 6, height = 2, command = lambda val = key:self.uc_disp(val))
                buttons.grid(row = y + 200, column = x + 200, ipadx = .05, ipady = .05, padx = 10, pady = 10)

    def uc_disp(self, val):            
        global USERNAME
        global PIN
        pin = self.controller.data["uc_passcode"].get()

        with sqlite3.connect(file) as db:
            c = db.cursor()

        c.execute("SELECT * FROM info WHERE username = ?", (USERNAME,))
        result = c.fetchall()

        if val == "*":
            self.uc_key.delete('0', 'end')
            PIN = ""
            self.uc_key.insert('0', tk.END)
        elif val == "#":
            if result:
                for i in result:
                    # Check if pin is correct
                    if(i[2] == pin):
                        # Will show frame saying passcode is correct
                        self.controller.after(100,self.correct)
                        # will fo to user info frame
                        self.controller.after(2000, self.u_info)
                        self.uc_key.delete('0', 'end')
                    else:
                        # show error frame if passcode is incorrect
                        self.controller.after(100, self.error)
                        # Will go back to profiles frame
                        self.controller.after(2000, self.prof)
                        self.uc_key.delete("0", "end")
            PIN = ""
        else:
            PIN += val
            self.uc_key.insert('end', val)

    def error(self):
        self.controller.show_frame("UserConfirm_Denied")
    def correct(self):
        self.controller.show_frame("UserConfirm_Access")
    def u_info(self):
        self.controller.show_frame("UserInfo")
    def prof(self):
        self.controller.show_frame("Profiles")

# Error frame when passcode is incorrect in startup menu
class Error(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "red")

        label = tk.Label(self, text = "ERROR! Incorrect Passcode, Please Try Again!", font = "Arial 25", bg = "red", fg = "orange")
        label.place(x=512, y = 200, anchor = "center")

        again = tk.Button(self, text = "Try Again", command = lambda: self.controller.show_frame("StartUp"), font = "Arial 18")
        again.place(x = 490, y = 500)

# error frame when new user's passcode do not match
class Error2(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "red")

        label = tk.Label(self, text = "ERROR! Incorrect Passcode, Please Try Again!", font = "Arial 25", bg = "red", fg = "orange")
        label.place(x=512, y = 200, anchor = "center")

        again = tk.Button(self, text = "Try Again", command = lambda: self.controller.show_frame("NewUser"), font = "Arial 18")
        again.place(x = 490, y = 500)

# error frame when admin passcode is entered incorrectly
class AdminError(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "red")

        label = tk.Label(self, text = "ERROR! Incorrect Passcode, Please Try Again!", font = "Arial 25", bg = "red", fg = "orange")
        label.place(x=512, y = 200, anchor = "center")

        again = tk.Button(self, text = "Try Again", command = lambda: self.controller.show_frame("Profiles"), font = "Arial 18")
        again.place(x = 490, y = 500)

class DeleteAdminError(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "red")

        label = tk.Label(self, text = "ERROR! Incorrect Passcode, Could Not Delete Information", font = "Arial 25", bg = "red", fg = "orange")
        label.place(x=512, y = 200, anchor = "center")

        again = tk.Button(self, text = "Try Again", command = lambda: self.controller.show_frame("Admin"), font = "Arial 18")
        again.place(x = 490, y = 500)

# error frame when admin enters incorrect passcode when editing a user's info
class EditAdminError(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "red")

        label = tk.Label(self, text = "ERROR! Incorrect Passcode, Could Not Update Information", font = "Arial 25", bg = "red", fg = "orange")
        label.place(x=512, y = 200, anchor = "center")

        again = tk.Button(self, text = "Try Again", command = lambda: self.controller.show_frame("Admin"), font = "Arial 18")
        again.place(x = 490, y = 500)

# success frame when face scan is successful
class Successful(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'green')

        success = tk.Label(self, text = "FACIAL SCAN SUCCESSFUL\nWELCOME", bg = 'green', fg = 'yellow', font = "Arial 30")
        success.place(x=512, y = 200, anchor = "center")

# Denied frame when user's face is scanned
class Denied(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'red')

        denied = tk.Label(self, text = "FACIAL SCAN DENIED\nGOING BACK TO HOME SCREEN", bg = 'red', fg = 'green', font = "Arial 30")
        denied.place(x=512, y = 200, anchor = "center")

# denied frame when trying to access their profile through face scan
class ProfileDenied(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'red')

        denied = tk.Label(self, text = "FACIAL SCAN DENIED\nGOING BACK TO HOME SCREEN", bg = 'red', fg = 'green', font = "Arial 30")
        denied.place(x=512, y = 200, anchor = "center")

# accept frame when trying to access user profile
class ProfileAccepted(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = "green")

        success = tk.Label(self, text = "FACIAL SCAN SUCCESSFUL", bg = 'green', fg = 'yellow', font = "Arial 30")
        success.place(x=512, y = 200, anchor = "center")

# Frame shown when user passcode is correct, will go to user profile frame
class UserConfirm_Access(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'green')

        success = tk.Label(self, text = "Passcode Correct, Going to User Profile", bg = 'green', fg = 'yellow', font = "Arial 30")
        success.place(x=512, y = 200, anchor = "center")

# Frame shown when user enters incorrect passcode
class UserConfirm_Denied(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'red')

        denied = tk.Label(self, text = "Incorrect Passcode", bg = 'red', fg = 'green', font = "Arial 30")
        denied.place(x=512, y = 200, anchor = "center")

# Frame shown when entered passcode correctly when using external keypad
class Successful_Keypad(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'green')

        label = tk.Label(self, text = "Passcode Correct, Opening Lock", bg = 'green', fg = 'yellow', font = "Arial 30")
        label.place(x=512, y = 200, anchor = "center")

# denied frame when passcode is entered incorrectly when using external keypad
class Denied_Keypad(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.configure(background = 'red')

        denied = tk.Label(self, text = "Incorrect Passcode\nGoing Back To Home Screen", bg = 'red', fg = 'green', font = "Arial 30")
        denied.place(x=512, y = 200, anchor = "center")

if __name__ == '__main__':
    app = FaceRecognition()
    app.title("Face Recognition Door Lock") # title of the GUI
    app.geometry("1000x600+0+0")    # resize frame to almost fit enire display screen
    app.mainloop()