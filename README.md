# pycoil-tagger
Third-party, open source, Python app for communicating with Recoil laser taggers

Written in Python 2.7. No where near complete.

Development
------------
This was written using IntelliJ community edition. I created an sftp connection to my Raspberry Pi Zero W on my local network. Editing code then became as simple as changing it locally and syncing onto the device. I use VNC to connect with the device and control the app, and output to a log file that I can tail in a shell session to see what output I am getting.

This app is in EARLY stages. It is barely more than a few Proof of Concept parts that are just beginning to come together in one app. I am using Blinker for signals/events, and I rolled my own VERY bare bones UI on top of Pygame. This is NOT set up as a production app and does not have things like well listed requirements, or any documentation.

The networking POC is technically net-compatible with SimpleCoil. It uses the same broadcast technique for discovery and currently is capable of sending out a JOIN request to SimpleCoil. I've verified this works but have done no more than that.

Installation
------------

Uses bluepy module for python, a "Python interface to Bluetooth LE on Linux": 
https://github.com/IanHarvey/bluepy

To install the current released version, on most Debian-based systems:

    $ sudo apt-get install python-pip libglib2.0-dev
    $ sudo pip install bluepy
