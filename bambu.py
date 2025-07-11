from datetime import datetime, timedelta
from pathlib import Path

import paho.mqtt.client as mqtt
import json
import ssl
import webcolors

OUTPUT_PATH = './'

values = {}
bambuCredentials = {}


def split_string(string):
    tuple_result = (int(string[:2],16), int(string[2:4],16), int(string[4:6],16))
    return tuple_result

# Expected input: 6 character hex string
def rgb_to_color_name(rgb):
    try:
        color_tuple = split_string(rgb)
        color_name = webcolors.rgb_to_name(color_tuple)
    except ValueError:
        # If the RGB value doesn't match any known color, return the hex code with a 0x prefeix
        color_name = f"0x{rgb}"
    return color_name



# The callback for when the client receives a CONNACK response from the server.
def on_connect(callback):
    def _on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        callback(client, userdata, flags, rc)

        # Bambu requires you to subscribe promptly after connecting or it forces a discconnect
        client.subscribe(f"device/{bambuCredentials['serial']}/report")

    return _on_connect


def on_disconnect(callback):
    def _on_disconnect(client, userdata, rc):
        print("Disconnected with result code " + str(rc))
        callback(client, userdata, rc)
        # Handle disconnection logic here if needed
    return _on_disconnect


prevTelemetry = {}

# The callback for when a PUBLISH message is received from the server.
# I'm really only using msg parameter here, but need to keep the first 2 args to match
# the callback signature
def on_message(callback):
    def _on_message(client, userdata, msg):
        global prevTelemetry
        # Current date and time
        now = datetime.now()
        doc = json.loads(msg.payload)
        # Have something to look at on screen so you know it's spinning
        # print(doc)
        output_dir = Path(OUTPUT_PATH)
        # JSON blobs written just for debug convenience
        telem_json_path = output_dir / "telemetry.json"
        telem_json_err_path = output_dir / "telemetry.err.txt"

        # only reason I split these into separate files was so they could
        # easily be modeled as separate text boxes in OBS
        telem_text_path = output_dir / "telemetry.txt"
        ams_text_path = output_dir / "ams.txt"

        try:
            # Write the raw JSON first incase there's a key error when we start trying to access it
            with telem_json_path.open("w") as fp:
                prevTelemetry = { **prevTelemetry, **doc }
                fp.write(json.dumps(prevTelemetry))

            
            if not doc:
                return

            globals()['values'] = dict(values, **doc['print'])

            # send values to telementry callback
            callback(values)
            # print(values)

            layer = values.get('layer_num', '?')
            speed = values.get('spd_lvl', 2)
            speed_map = {1: 'Silent', 2: 'Standard', 3: 'Sport', 4: 'Ludacris'}

            min_remain = values['mc_remaining_time']
            # Time 15 minutes in the future
            future_time = now + timedelta(minutes=min_remain)
            future_time_str = future_time.strftime("%Y-%m-%d %H:%M")

            active_ams = values['ams']['tray_now']

            with telem_text_path.open("w") as fp:
                fp.write(f"Layer: {layer} ({values['mc_percent']} %)\n"
                        f"Nozzle Temp: {values['nozzle_temper']}/{values['nozzle_target_temper']}\n"
                        f"Bed Temp: {values['bed_temper']}/{values['bed_target_temper']}\n"
                        f"Finish ETA: {future_time_str}\n"
                        f"Speed: {speed_map[speed]}")

            with ams_text_path.open("w") as fp:
                for tray in values['ams']['ams'][0]['tray']:
                    tray_remain = ''
                    color_name = rgb_to_color_name(tray['cols'][0])
                    if active_ams == tray['id']:
                        active = " - In Use"
                    else:
                        active = ""
                    if tray['remain'] != -1:
                        tray_remain = f"({tray['remain']}% remain)"
                    if tray['tray_sub_brands'] == '':
                        tray_type = tray['tray_type']
                    else:
                        tray_type = tray['tray_sub_brands']
                    fp.write(f"Tray {tray['id']}: {tray_type} {color_name} {tray_remain}  {active}\n")

                if active_ams == "254":
                    active = " - In Use"
                else:
                    active = ""

                color_name = rgb_to_color_name(values['vt_tray']['cols'][0])

                fp.write(f"Ext. : {values['vt_tray']['tray_type']} {color_name} {active}")


        # Sometimes empty or diff doc structure returned
        # Swallow exception here and it'll just get retried next iteration
        except KeyError:
            print("Logging error json")
            # with telem_json_err_path.open("w") as fp:
                # fp.write(json.dumps(doc))

    return _on_message



def connect_mqtt(credentials, on_bambu_connect, on_telemetry_data, on_bambu_disconnect):
    
    print("Connecting to Bambu printer...")
    client = mqtt.Client()
    client.check_hostname = False

    globals()['bambuCredentials'] = dict(bambuCredentials, **credentials)

    client.on_connect = on_connect(on_bambu_connect)
    client.on_message = on_message(on_telemetry_data)
    client.on_disconnect = on_disconnect(on_bambu_disconnect)

    # set username and password
    # Username isn't something you can change, so hardcoded here
    client.username_pw_set(bambuCredentials['username'], bambuCredentials['access_code'])

    # These 2 lines are required to bypass self signed certificate errors, at least on my machine
    # these things can be finicky depending on your system setup
    client.tls_set(tls_version=ssl.PROTOCOL_TLS, cert_reqs=ssl.CERT_NONE)
    # client.tls_set_context(create_local_ssl_context())
    client.tls_insecure_set(True)

    client.connect(bambuCredentials['bambu_ip'], int(bambuCredentials['bambu_port']), 60)


    client.publish(f"device/{bambuCredentials['serial']}/request", '{"pushing": {"command": "start", "sequence_id": 0}}')
    # client.publish(f"device/{SERIAL}/report", '{"pushing": {"command": "start", "sequence_id": 0}}')
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    print(bambuCredentials['bambu_ip'], bambuCredentials['bambu_port'], bambuCredentials['serial'],  bambuCredentials['access_code'], bambuCredentials['username'])

    return client
