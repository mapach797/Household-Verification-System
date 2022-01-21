#Household-Verification-System

This is a Senior Project for CSUSB.

The aim of this project is to create a verification system for household owners who want to add extra security. We want homeowners to feel safe, and with this product, we can give them more security.

This project was created using a Raspberry Pi, PiCamera, 4x4 Membrane Keypad for the Raspberry Pi, and a solenoid lock.

A user-friendly Graphical User Interface (GUI) was created to help the user navigate the product, with a Database that gets created, using SQLite3, when the admin/first user creates their profile. The Haar-Cascade Classifier was used to train a model that will contain the user's pictures, and will be able to unlock the solenoid lock when it recognizes the user within a certain range of acceptance. As this is a project, we decided to have a mid-range acceptance, as the model would need thousands of pictures of the user to train it so that the acceptance percentage is higher. 
