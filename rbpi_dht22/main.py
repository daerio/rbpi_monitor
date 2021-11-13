#!/usr/bin/python3

import os
import csv
import ssl
import json
import logging
from configparser import ConfigParser
from datetime import datetime
import smtplib
from smtplib import SMTPException
import Adafruit_DHT


# Get current date and time
datetime_now = datetime.now().isoformat()

# Read config file
curr_dir = os.path.dirname(__file__)
config = ConfigParser()
config_file_path = curr_dir + "/main.conf"
config.read(config_file_path)

# Read main config
use_f = config.getboolean("main", "use_f")

# Read SMTP config
smtp_host = config.get("smtp", "host")
smtp_port = config.getint("smtp", "port")

# Read mail config
send_email = config.getboolean("email", "send_email")
subject = config.get("email", "subject")
sender = config.get("email", "sender")
sender_name = config.get("email", "sender_name")
receiver = config.get("email", "receiver")
receivers = [receiver]
receiver_name = config.get("email", "receiver_name")


def do_send_email(subject, text):
    # SSL setup
    _DEFAULT_CIPHERS = (
        "ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:"
        "DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:"
        "!eNULL:!MD5"
    )

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3

    context.set_ciphers(_DEFAULT_CIPHERS)
    context.set_default_verify_paths()
    context.verify_mode = ssl.CERT_REQUIRED

    message = f"""From: From {sender_name} <{sender}>
    To: To {receiver_name} <{receiver}>
    Subject: {subject}

    {text}
    """

    try:
        smtpObj = smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=60)
        smtpObj.starttls(context=context)
        smtpObj.sendmail(sender, receivers, message)
    except SMTPException as e:
        logging.error("Error: " + str(e))
    except Exception as e:
        logging.error("Error: " + str(e))


sensor_type = Adafruit_DHT.DHT22
sensors = config.get("main", "sensors")
sensors_list = json.loads(sensors)

log_dir = "/var/log/rbpi_monitor"

log_folder_exists = os.path.exists(log_dir)
if not log_folder_exists:
    os.mkdir(log_dir)

logging.basicConfig(filename=log_dir + "/dht22_error.log", level=logging.ERROR)

log_file_exists = os.path.exists(log_dir + "/dht22_log.csv")
if log_file_exists:
    log_file = open(log_dir + "/dht22_log.csv", "a", encoding="UTF8", newline="")
    log_writer = csv.writer(log_file)
else:
    log_file = open(log_dir + "/dht22_log.csv", "w", encoding="UTF8", newline="")
    # Create the log file, the csv writer and write a header since none existed.
    log_writer = csv.writer(log_file)
    log_writer.writerow(["Datetime", "GPIO#", "Label", "Temperature", "Humidity"])


mail_body = ""

# Loop over all specified sensors
for sensor in sensors_list:
    try:
        # Query the sensor for data
        humidity, temp = Adafruit_DHT.read_retry(
            sensor=sensor_type, pin=sensor.get("gpio"), retries=15, delay_seconds=2
        )

        if use_f:
            temp = temp * (9 / 5) + 32
            temp_string = f"{temp:.2f} °F"
        else:
            temp_string = f"{temp:.2f} °C"

        # Write a row to the csv log file
        log_writer.writerow(
            [datetime_now, sensor.get("gpio"), sensor.get("label"), temp, humidity]
        )

        if (
            # Use specified min, max of DHT22 sensors if no other values are given.
            temp > float(sensor.get("max_temp", "80.0"))
            or temp < float(sensor.get("min_temp", "-40.0"))
            or humidity > float(sensor.get("max_hum", "100.0"))
            or humidity < float(sensor.get("min_hum", "0.0"))
        ):
            # At least one value is out of bounds -> send warning email
            if not mail_body:
                mail_body += (
                    "This is an automated warning. "
                    "The following sensors have issued warnings:\n"
                )
            sensor_string = sensor.get("label", sensor.get("gpio"))
            mail_body += (
                f"Sensor: {sensor_string} "
                f"Temperature: {temp_string} Humidity: {humidity} %\n"
            )

    except Exception as e:
        logging.error("Error: " + str(e))

# Close log file
log_file.close()

# Send mail if we have any warnings
if send_email and mail_body:
    do_send_email(subject=subject, text=mail_body)
