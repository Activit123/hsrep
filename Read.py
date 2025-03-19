#!/usr/bin/env python3
import spidev
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time

def check_spi_connection():
    spi = spidev.SpiDev()
    try:
        spi.open(0, 0)  # Open SPI bus 0, device 0
        spi.max_speed_hz = 1250000 # Set speed (1 MHz recommended for MFRC522)
        spi.xfer2([0x00])  # Try sending a dummy command
        print("SPI communication with RFID module is active.")
        return True  # Module is detected
    except Exception as e:
        print("Error: RFID module not detected. Check connections! \n", e)
        return False  # Module is not connected
    finally:
        spi.close()

def read_rfid():
    reader = SimpleMFRC522()
    try:
        print("Apropiați un tag RFID de cititor...")
        tag_id, tag_text = reader.read()  # Blocking call until a tag is read
        print("RFID citit cu succes!")
        print("ID tag:", tag_id)
        print("Text:", tag_text)
    except Exception as e:
        print("Eroare la citirea RFID:", e)
    finally:
        GPIO.cleanup()

def main():
    # First, check if the RFID module is connected
    if check_spi_connection():
        # Now, attempt to read an RFID tag
        read_rfid()
    else:
        print("RFID module is not connected. Exiting.")

if __name__ == '__main__':
    main()
