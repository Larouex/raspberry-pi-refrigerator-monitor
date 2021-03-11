# ==================================================================================
#   File:   serialemulator.py
#   Author: Larry W Jordan Jr (larouex@gmail.com)
#   Use:    This class creates serial connection and emits a CSV to emulate
#           telemetry values from a ColdPack unit.
#
#   https://github.com/Larouex/cold-hub-azure-iot-central
#
#   (c) 2021 Larouex Software Design LLC & Zena is Awesome Software & Zena is Awesome Software
#   This code is licensed under MIT license (see LICENSE.txt for details)
# ==================================================================================
import time, serial, asyncio, requests, datetime, io, json
import logging

# Pub Sub Support
from pubsub import pub

# our classes
from classes.config import Config
from classes.secrets import Secrets

class SerialEmulator():

    def __init__(self, Log):
      self.logger = Log

      # Load configuration
      config = Config(self.logger)
      self.config = config.data

      # Secrets Cache
      self.secrets = Secrets(self.logger)
      self.secrets_data = self.secrets.data

      self.serial_emulator_port = None

      # Configure the National Renewable Energy Labratory
      self.NREUrl = self.config["NREUrl"].format(api_key = self.secrets_data["NREApiKey"])

    # -------------------------------------------------------------------------------
    #   Function:   translate
    #   Usage:      Takes the emitted CSV and returns a Json Payload
    # -------------------------------------------------------------------------------
    def translate(self, data):

      csv_string = data.decode()
      csv_array = csv_string.split(",")

      telemetry_dict = {}
      index = 0
      name = None

      for val in csv_array:
        if index == 0:
          name = val
          index = 1
        else:
          telemetry_dict[name] = val
          index = 0

      return telemetry_dict

    # -------------------------------------------------------------------------------
    #   Function:   run
    #   Usage:      Starts the Serial Emulator and writes values
    # -------------------------------------------------------------------------------
    async def run(self):

      msgCnt = 0
      first = True

      #try:
        
      while True:
        
        if first == False:
          print("Waiting [%s] Seconds before sending Telemetry (defined by TelemetryFrequencyInSeconds)" % self.config["TelemetryFrequencyInSeconds"])
          await asyncio.sleep(self.config["TelemetryFrequencyInSeconds"])
        else:
          first = False
        
        msgCnt = msgCnt + 1
        payload = []
        
        for variable in self.config["SerialEmulator"]["Variables"]:
          
          component_name = variable["Name"]
          data = self.create_instance_root(component_name)

          for twin_property in variable["TwinProperties"]:
            result = self.get_twin_property(twin_property, msgCnt)
            data["Properties"].append(result)
          
          for telemetry in variable["Telemetries"]:
            result = self.get_telemetry(telemetry, msgCnt)
            data["Telemetries"].append(result)
          
          payload.append(data)
        
        self.logger.info("PAYLOAD: [{0}]".format(payload)

        # post to the queue
        self.serial_emulator_port.flush()
        payload_string = json.dumps(payload) 
        self.serial_emulator_port.write(payload_string.encode())
        pub.sendMessage("telemetry", result=payload)

        payload = []

      return

      except Exception as ex:
        self.logger.error("[ERROR] %s" % ex)
        self.logger.error("[TERMINATING] We encountered an error in Cold Hub SerialEmulator Run::run()" )
      
      finally:
        self.serial_emulator_port.close()

    # -------------------------------------------------------------------------------
    #   Function:   setup
    #   Usage:      The setup function preps the configuration for the Cold Hub SerialEmulator
    # -------------------------------------------------------------------------------
    async def setup(self):

      try:

        print("[%s]: Setting up the Cold Hub SerialEmulator" % self.config["NameSpace"])
        
        # Connect our Device for Telemetry and Updates
        self.serial_emulator_port = serial.Serial(
          port = "/dev/" + self.config["USBSerialEmulator"]["Port"],
          baudrate = self.config["USBSerialEmulator"]["BaudRate"],
          parity = serial.PARITY_NONE,
          stopbits = serial.STOPBITS_ONE,
          bytesize = serial.EIGHTBITS,
          timeout = 1
        )
       
        # Verbose
        self.logger.info("[{0}]: USB Port {1}".format(self.config["NameSpace"], self.config["USBSerialEmulator"]["Port"]))
        self.logger.info("[{0}]: Baud Rate {1}".format(self.config["NameSpace"], self.config["USBSerialEmulator"]["BaudRate"]))
        self.logger.info("[%s]: Completed setting up the Cold Hub SerialEmulator" % self.config["NameSpace"])

      except Exception as ex:
        self.logger.error("[ERROR] %s" % ex)
        self.logger.error("[TERMINATING] We encountered an error in Cold Hub SerialEmulator Setup::setup()" )

      return

    # -------------------------------------------------------------------------------
    #   Function:   get_nre_data
    #   Usage:      Loads the configuration from file
    # -------------------------------------------------------------------------------
    def get_nre_data(self):
      headers = {
          'content-type': "application/x-www-form-urlencoded",
          'cache-control': "no-cache"
      }

      payload = "names=2012&leap_day=false&interval=60&utc=false&full_name=Honored%2BUser&email=honored.user%40gmail.com&affiliation=NREL&mailing_list=true&reason=Academic&attributes=dhi%2Cdni%2Cwind_speed_10m_nwp%2Csurface_air_temperature_nwp&wkt=MULTIPOINT(-106.22%2032.9741%2C-106.18%2032.9741%2C-106.1%2032.9741)"
      response = requests.request("POST", url, data=payload, headers=headers)
      return response.text

    # -------------------------------------------------------------------------------
    #   Function:   get_twin_property
    #   Usage:      Creates the Twin Property based on the rules
    # -------------------------------------------------------------------------------
    def get_twin_property(self, data, msgCnt):

      serial_string = "{0}".format(data["Name"])

      if data["UseRangeValues"] == "RangeValues":
        serial_string = serial_string + ',' + "{0}".format(data["RangeValues"][0])
      elif data["UseRangeValues"] == "Counter":
        serial_string = serial_string + ',' + str(msgCnt)
      elif "SelectIndex" in data["UseRangeValues"]:
        index = data["UseRangeValues"].split(":")
        serial_string = serial_string + ',' + "{0}".format(data["RangeValues"][int(index[1])])

      return serial_string

    # -------------------------------------------------------------------------------
    #   Function:   get_telemetry
    #   Usage:      Creates the Telemetry Value based on the rules
    # -------------------------------------------------------------------------------
    def get_telemetry(self, data, msgCnt):

      serial_string = "{0}".format(data["Name"])
            
      if data["UseRangeValues"] == "RangeValues":
        serial_string = serial_string + ',' + "{0}".format(data["RangeValues"][0])
      elif data["UseRangeValues"] == "Counter":
        serial_string = serial_string + ',' + str(msgCnt)
      elif "SelectIndex" in data["UseRangeValues"]:
        index = data["UseRangeValues"].split(":")
        serial_string = serial_string + ',' + "{0}".format(data["RangeValues"][int(index[1])])

      return serial_string

    # -------------------------------------------------------------------------------
    #   Function:   create_instance_root
    #   Usage:      Per Component Interface
    # -------------------------------------------------------------------------------
    def create_instance_root(self, Name):
      mapRoot = {
        "Name": Name,
        "Created": str(datetime.datetime.now()),
        "Properties": [
        ],
        "Telemetries": [
        ]
      }
      return mapRoot

    # -------------------------------------------------------------------------------
    #   Function:   serial_json_encode
    #   Usage:      Do the prep to send on the serial port
    # -------------------------------------------------------------------------------
    def serial_json_encode(self, the_dict):
        str = json.dumps(the_dict)
        binary = ' '.join(format(ord(letter), 'b') for letter in str)
        return binary


    # -------------------------------------------------------------------------------
    #   Function:   serial_json_decode
    #   Usage:      Unencode the result
    # -------------------------------------------------------------------------------
    def serial_json_decode(self, the_binary):
        jsn = ''.join(chr(int(x, 2)) for x in the_binary.split())
        d = json.loads(jsn)  
        return d