#!/usr/bin/python

# if we are going to use a display, check to
# see if we set RHSM_DISPLAY and set DISPLAY
# there

# idea being you can set RHSM_DISPLAY to
# a headless VNC server or x server etc
# and the test cases will display there
# instead of cluttering your window

import os


def set_display():
    if 'RHSM_DISPLAY' in os.environ:
        os.environ['DISPLAY'] = os.environ['RHSM_DISPLAY']
