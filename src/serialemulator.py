#!/home/Larouex/Python
# ==================================================================================
#   File:   verify.py
#   Author: Larry W Jordan Jr (larouex@gmail.com)
#   Use:    RefriderationMonitor Telemetry Emulator for Serial Output
#
#   https://github.com/Larouex/cold-hub-azure-iot-central
#
#   (c) 2021 Larouex Software Design LLC & Zena is Awesome Software & Zena is Awesome Software
#   This code is licensed under MIT license (see LICENSE.txt for details)
# ==================================================================================
import getopt, sys, time, string, threading, asyncio, os, serial
import logging as Log

# our classes
from classes.serialemulator import SerialEmulator
from classes.config import Config

# -------------------------------------------------------------------------------
#   Setup the Cold Hub Serial Emulator
# -------------------------------------------------------------------------------
async def setup_RefriderationMonitor_serial_emulator(RefriderationMonitorSerialEmulator):

  try:

    Log.info("[SETUP] setup_RefriderationMonitor_serial_emulator...")
    return await RefriderationMonitorSerialEmulator.setup()

  except Exception as ex:
    Log.error("[ERROR] %s" % ex)
    Log.error("[TERMINATING] We encountered an error in [setup_RefriderationMonitor_serial_emulator]" )
    return

# -------------------------------------------------------------------------------
#   Start the Cold Hub Serial Emulator Telemetry Loop
# -------------------------------------------------------------------------------
async def run_RefriderationMonitor_serial_emulator(RefriderationMonitorSerialEmulator):

    Log.info("[RUN] run_RefriderationMonitor_serial_emulator...")
    return await RefriderationMonitorSerialEmulator.run()

# -------------------------------------------------------------------------------
#   main()
# -------------------------------------------------------------------------------
async def main(argv):

  # execution state from args
  short_options = "hvd"
  long_options = ["help", "verbose", "debug"]
  full_cmd_arguments = sys.argv
  argument_list = full_cmd_arguments[1:]
  try:
    arguments, values = getopt.getopt(argument_list, short_options, long_options)
  except getopt.error as err:
    print (str(err))

  for current_argument, current_value in arguments:

    if current_argument in ("-h", "--help"):
      print("------------------------------------------------------------------------------------------------------------------------------------------")
      print("HELP for serialemulator.py")
      print("------------------------------------------------------------------------------------------------------------------------------------------")
      print("")
      print("  BASIC PARAMETERS...")
      print("")
      print("  -h or --help - Print out this Help Information")
      print("  -v or --verbose - Debug Mode with lots of Data will be Output to Assist with Debugging")
      print("  -d or --debug - Debug Mode with lots of DEBUG Data will be Output to Assist with Tracing and Debugging")
      print("------------------------------------------------------------------------------------------------------------------------------------------")
      return

    if current_argument in ("-v", "--verbose"):
      Log.basicConfig(format="%(levelname)s: %(message)s", level = Log.INFO)
      Log.info("Verbose Logging Mode...")
    else:
      Log.basicConfig(format="%(levelname)s: %(message)s")

    if current_argument in ("-d", "--debug"):
      Log.basicConfig(format="%(levelname)s: %(message)s", level = Log.DEBUG)
      Log.info("Debug Logging Mode...")
    else:
      Log.basicConfig(format="%(levelname)s: %(message)s")

  # Configure
  RefriderationMonitor_serial_eumlator = SerialEmulator(Log)
  await setup_RefriderationMonitor_serial_emulator(RefriderationMonitor_serial_eumlator)
  Log.info("[SERVER] Instance Info (RefriderationMonitor_serial_eumlator): %s" % RefriderationMonitor_serial_eumlator)

  # Start the loop
  await run_RefriderationMonitor_serial_emulator(RefriderationMonitor_serial_eumlator)

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
