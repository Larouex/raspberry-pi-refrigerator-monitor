# ==================================================================================
#   File:   monitor.py
#   Author: Larry W Jordan Jr (larouex@gmail.com)
#   Use:    This class will return and instance of the Cold Hub Monitor and with a 
#           runing monitoring loop
#
#   https://github.com/Larouex/cold-hub-azure-iot-central
#
#   (c) 2021 Larouex Software Design LLC & Zena is Awesome Software & Zena is Awesome Software
#   This code is licensed under MIT license (see LICENSE.txt for details)
# ==================================================================================
import json, sys, time, string, threading, asyncio, os, copy, datetime, serial
import board, busio, adafruit_am2320, kwargs
import RPi.GPIO as GPIO
import logging

# from prettytable import PrettyTable
from texttable import Texttable

# Pub/Sub Support
from pubsub import pub

# our classes
from classes.config import Config
from classes.secrets import Secrets
from classes.deviceclient import DeviceClient
from classes.devicescache import DevicesCache
from classes.serialemulator import SerialEmulator

class Listener:

    def __init__(self):
        self.payload = None

    def __call__(self, **kwargs):
        print("result")
        self.payload =  kwargs["result"]
        print(self.payload)
        print("ambient")
        self.payload =  kwargs["ambient"]
        print(self.payload)

    def read_payload(self):
        print("READ PAYLOAD  ***")
        return self.payload

class Monitor():

    def __init__(self, Log):
      self.logger = Log

      # Load configuration
      self.config = []
      self.load_config()

      # --------------------------------------------------------
      # Smoothing Value
      # --------------------------------------------------------
      self.smoothing_value = 1

      # --------------------------------------------------------
      # Worker Variables for Current Temp & Humidity
      # --------------------------------------------------------
      self.Temperature = 0.0
      self.Humidity = 0.0

      # --------------------------------------------------------
      # Payload Variable Names for Current Temp & Humidity
      # --------------------------------------------------------
      self.TemperatureMapName = "temperature"
      self.HumidityMapName = "humidity"

      # --------------------------------------------------------
      # Worker Variables for last Read Temp
      # --------------------------------------------------------
      self.LastTemperature = 0.0
      self.LastHumidity = 0.0

      # --------------------------------------------------------
      # Setup the GPIO BCM Variables for Status
      # --------------------------------------------------------
      self.RedPin = self.config["Status"]["Pins"]["Red"]
      self.GreenPin = self.config["Status"]["Pins"]["Green"]
      self.BluePin = self.config["Status"]["Pins"]["Blue"]
      self.RedColor = 1
      self.GreenColor = 2
      self.BlueColor = 3

      # Telemetry Mapping
      self.interfaces_instances = {}
      self.capabilities_instances = {}

      # meta
      self.application_uri = None
      self.namespace = None
      self.device_capability_model_id = None
      self.device_capability_model = []
      self.device_name_prefix = None
      self.ignore_interface_ids = []

      # Device Information
      self.device_cache = {}
      self.load_devicecache()

      # Azure Device
      self.device_client = None

      # Objects for i2c
      self.i2c = busio.I2C(board.SCL, board.SDA)
      self.sensor = adafruit_am2320.AM2320(self.i2c)

      # Serial
      self.serial_emulator = SerialEmulator(Log)
      self.serial_emulator_port = None
      
      # Pub Sub
      self.listener = Listener()
      self.subscribed_payload = None

    # -------------------------------------------------------------------------------
    #   Function:   run
    #   Usage:      The start function starts the OPC Server
    # -------------------------------------------------------------------------------
    async def run(self):

      msgCnt = 0

      # Set device client from Azure IoT SDK and connect
      device_client = None
      first = True
      self.setColor(self.RedColor)
      await asyncio.sleep(5.0)

      try:
        
        # Connect our Device for Telemetry and Updates
        for device in self.device_cache["Devices"]:
          self.logger.info("[Cold Hub] CONNECTING TO IOT CENTRAL: %s" % device["Device"]["Name"])
          device_client = DeviceClient(self.logger, device["Device"]["Name"])
          await device_client.connect()

        # Subscribe to the Telemetry Server Publication of Telemetry Data
        pub.subscribe(self.listener, pub.ALL_TOPICS)

        while True:

          if first == False:
            print("Waiting [%s] Seconds before reading Sensors (defined by TelemetryFrequencyInSeconds)" % self.config["TelemetryFrequencyInSeconds"])
            self.setColor(self.BlueColor)
            await asyncio.sleep(self.config["TelemetryFrequencyInSeconds"])
          else:
            first = False

          msgCnt = msgCnt + 1

          # READ TEMP & HUMIDITY
          self.Temperature = self.sensor.temperature
          self.Humidity = self.sensor.relative_humidity
          
          # Subscribe to the Telemetry Server Publication of Telemetry Data
          self.subscribed_payload = self.listener.read_payload()
          print("***")
          print(self.subscribed_payload)
          print("***")
          
          # READ FROM SERIAL TELEMETRY
          serial_read = self.serial_emulator_port.readline()
          print("read serial")
          print(serial_read)

          # Conversions
          if self.config["TemperatureFormat"] == "F":
            self.Temperature = self.convert2fahrenheit(self.Temperature)

          table = Texttable()
          table.set_deco(Texttable.HEADER)
          table.set_cols_dtype(["t", "f", "f", "f"])
          table.set_cols_align(["l", "r", "r", "r"])
          table.add_rows([["Sensor",  "Temperature[{0}]".format(self.config["TemperatureFormat"]), "Last Temperature[{0}]".format(self.config["TemperatureFormat"]), "Smoothing"],
                          ["Temperature", self.Temperature, self.LastTemperature, self.Temperature / self.smoothing_value],
                          ["Humidity", self.Humidity, self.LastHumidity, self.Humidity  / self.smoothing_value]])

          print(table.draw())
          print("***")

          # Capture Last Values
          self.LastTemperature = self.Temperature
          self.LastHumidity = self.Humidity

          # Smooth Values
          self.Temperature = self.Temperature / self.smoothing_value
          self.Humidity = self.Humidity / self.smoothing_value

          # Send Data to IoT Central
          self.telemetry_dict = {}
          self.telemetry_dict[self.TemperatureMapName] = self.Temperature
          self.telemetry_dict[self.HumidityMapName] = self.Humidity
          #self.telemetry_dict = {**self.telemetry_dict, **self.serial_emulator.translate(serial_read)}
          self.logger.info("[Cold Hub] SENDING PAYLOAD IOT CENTRAL")
          #await device_client.send_telemetry(self.telemetry_dict, self.config["Model"]["DeviceCapabilityModelId"], self.config["Model"]["NameSpace"])
          await device_client.send_telemetry(self.telemetry_dict, "dtmi:RefriderationMonitorStorage:ambient;1", "ambient")
          
          
          self.logger.info("[Cold Hub] SUCCESS")
          self.setColor(self.GreenColor)
          await asyncio.sleep(5.0)

        return

      except Exception as ex:
        self.logger.error("[ERROR] %s" % ex)
        self.logger.error("[TERMINATING] We encountered an error in Cold Hub Monitor Run::run()" )
      
      except KeyboardInterrupt:
        self.p_R.stop()
        self.p_G.stop()
        self.p_B.stop()
        for i in self.pins:
          GPIO.output(self.pins[i], GPIO.HIGH)    # Turn off all leds
        GPIO.cleanup()

      finally:
        await device_client.disconnect()

    # -------------------------------------------------------------------------------
    #   Function:   setup
    #   Usage:      The setup function preps the configuration for the Cold Hub Monitor
    # -------------------------------------------------------------------------------
    async def setup(self):

      try:

        print("[%s]: Setting up the Cold Hub Monitor" % self.config["NameSpace"])

        # --------------------------------------------------------
        # GPIO
        # --------------------------------------------------------
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # --------------------------------------------------------
        # Set Mode Leds (STATUS) and Defaults
        # --------------------------------------------------------
        GPIO.setup(self.RedPin, GPIO.OUT)
        GPIO.output(self.RedPin, GPIO.HIGH)
        GPIO.setup(self.GreenPin, GPIO.OUT)
        GPIO.output(self.GreenPin, GPIO.HIGH)
        GPIO.setup(self.BluePin, GPIO.OUT)
        GPIO.output(self.BluePin, GPIO.HIGH)

        # Verbose
        self.logger.info("[{0}]: Alert Pin {1}".format(self.config["NameSpace"], self.config["Status"]["Pins"]["Red"]))
        self.logger.info("[{0}]: Wait Pin {1}".format(self.config["NameSpace"], self.config["Status"]["Pins"]["Green"]))
        self.logger.info("[{0}]: Good Pin {1}".format(self.config["NameSpace"], self.config["Status"]["Pins"]["Blue"]))

        self.serial_emulator_port = serial.Serial(
          port = "/dev/" + self.config["SerialPortEmulator"]["Port"],
          baudrate = self.config["SerialPortEmulator"]["BaudRate"],
          parity = serial.PARITY_NONE,
          stopbits = serial.STOPBITS_ONE,
          bytesize = serial.EIGHTBITS,
          timeout = 1
        )

        # Verbose
        self.logger.info("[{0}]: USB Port {1}".format(self.config["NameSpace"], self.config["USBSerialEmulator"]["Port"]))
        self.logger.info("[{0}]: Baud Rate {1}".format(self.config["NameSpace"], self.config["USBSerialEmulator"]["BaudRate"]))

      except Exception as ex:
        self.logger.error("[ERROR] %s" % ex)
        self.logger.error("[TERMINATING] We encountered an error in Cold Hub Monitor Setup::setup()" )

      print("[%s]: Completed setting up the Cold Hub Monitor" % self.config["NameSpace"])

      return

    # -------------------------------------------------------------------------------
    #   Function:   convert2fahrenheit
    #   Usage:      Takes celsius Input and Returns Fahrenheit Conversion
    # -------------------------------------------------------------------------------
    def convert2fahrenheit(self, celsius):
      return (celsius * 1.8) + 32

    # -------------------------------------------------------------------------------
    #   Function:   load_config
    #   Usage:      Loads the configuration from file
    # -------------------------------------------------------------------------------
    def load_config(self):

      config = Config(self.logger)
      self.config = config.data
      return

    # -------------------------------------------------------------------------------
    #   Function:   load_devicecache
    #   Usage:      Loads the Device that have been registered and provisioned.
    #               This file is generated from the as-is state of the system
    #               when the OpcUaServer is started.
    # -------------------------------------------------------------------------------
    def load_devicecache(self):

      devicecache = DevicesCache(self.logger)
      self.device_cache = devicecache.data
      return

    def setColor(self, color):
      if color == self.RedColor:
        GPIO.output(self.RedPin, GPIO.LOW)
        GPIO.output(self.GreenPin, GPIO.HIGH)
        GPIO.output(self.BluePin, GPIO.HIGH)
      elif color == self.GreenColor:
        GPIO.output(self.RedPin, GPIO.HIGH)
        GPIO.output(self.GreenPin, GPIO.LOW)
        GPIO.output(self.BluePin, GPIO.HIGH)
      elif color == self.BlueColor:
        GPIO.output(self.RedPin, GPIO.HIGH)
        GPIO.output(self.GreenPin, GPIO.HIGH)
        GPIO.output(self.BluePin, GPIO.LOW)
      return

