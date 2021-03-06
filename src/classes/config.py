# ==================================================================================
#   File:   config.py
#   Author: Larry W Jordan Jr (larouex@gmail.com)
#   Use:    Handler for Config
#
#   https://github.com/Larouex/cold-hub-azure-iot-central
#
#   (c) 2021 Larouex Software Design LLC & Zena is Awesome Software & Zena is Awesome Software
#   This code is licensed under MIT license (see LICENSE.txt for details)
# ==================================================================================
import json
import logging

class Config():

    def __init__(self, logger):
        self.logger = logger
        self.load_file()

    def load_file(self):
        with open('config.json', 'r') as config_file:
            self.data = json.load(config_file)
            alerts = self.load_alerts()
            self.logger.debug(alerts["Alerts"]["Config"]["Loaded"].format(self.data))

    def load_alerts(self):
        with open('alerts.json', 'r') as alerts_file:
            return json.load(alerts_file)