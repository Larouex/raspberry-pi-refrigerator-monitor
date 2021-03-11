# ==================================================================================
#   File:   listener.py
#   Author: Larry W Jordan Jr (larouex@gmail.com)
#   Use:    Listen to the topic from a subscription to the serial emulator
#
#   Online:   #   https://github.com/Larouex/cold-hub-azure-iot-central
#
#   (c) 2021 Larouex Software Design LLC
#   This code is licensed under MIT license (see LICENSE.txt for details)
# ==================================================================================
import kwargs
from pubsub import pub

class Listener:

    def __init__(self):
      self.payload = None

    def __call__(self, **kwargs):
      # read and parse the payload
      self.payload =  kwargs["result"]

    def read_payload(self):
      return self.payload
