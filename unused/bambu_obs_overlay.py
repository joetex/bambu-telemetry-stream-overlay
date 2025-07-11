from datetime import datetime, timedelta
from pathlib import Path

import paho.mqtt.client as mqtt
import json
import ssl
import webcolors

# Found on printer touch screen under Settings (hex icon) -> Network
BAMBU_IP_ADDRESS = '192.168.18.10'
ACCESS_CODE = '16986605'

# Found on printer touch screen under Settings (hex icon) -> General
SERIAL = '01P00C480600128'

# What ever directory you want the output files written to
OUTPUT_PATH = './'

values = {}


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    # Bambu requires you to subscribe promptly after connecting or it forces a discconnect
    client.subscribe(f"device/{SERIAL}/report")

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

# The callback for when a PUBLISH message is received from the server.
# I'm really only using msg parameter here, but need to keep the first 2 args to match
# the callback signature
def on_message(client, userdata, msg):
    # Current date and time
    now = datetime.now()
    doc = json.loads(msg.payload)
    # Have something to look at on screen so you know it's spinning
    print(doc)
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
            fp.write(json.dumps(doc))

        if not doc:
            return

        globals()['values'] = dict(values, **doc['print'])

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
        with telem_json_err_path.open("w") as fp:
            fp.write(json.dumps(doc))




def create_local_ssl_context():
    """
    This context validates the certificate for TLS connections to local printers.
    It additionally requires calling `context.wrap_socket(sock, servername=printer_serial_number)`
    for the Server Name Indication (SNI).
    """
    context = ssl.create_default_context(cafile="ca_cert.pem")
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


class MQTTSClient(mqtt.Client):
    """
    MQTT Client that supports custom certificate Server Name Indication (SNI) for TLS.
    see https://github.com/eclipse-paho/paho.mqtt.python/issues/734#issuecomment-2256633060
    """

    def __init__(self, *args, server_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._server_name = server_name

    def _ssl_wrap_socket(self, tcp_sock) -> ssl.SSLSocket:
        orig_host = self._host
        if self._server_name:
            self._host = self._server_name
        res = super()._ssl_wrap_socket(tcp_sock)
        self._host = orig_host
        return res


def connect_local_mqtt(hostname, device_id, access_code):
    client = MQTTSClient(server_name=device_id)
    client.tls_set_context(create_local_ssl_context())
    client.username_pw_set("bblp", access_code)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(hostname, port=8883, keepalive=60)

    
    client.loop_forever()

    return client


def connect_cloud_mqtt(username, access_token):
    client = MQTTSClient()
    client.tls_set()
    client.username_pw_set(username, access_token)

   

    client.connect("us.mqtt.bambulab.com", port=8883, keepalive=60)


    return client



# client = connect_local_mqtt(BAMBU_IP_ADDRESS, SERIAL, ACCESS_CODE)



client = mqtt.Client()
client.check_hostname = False

client.on_connect = on_connect
client.on_message = on_message

# set username and password
# Username isn't something you can change, so hardcoded here
client.username_pw_set('bblp', ACCESS_CODE)

# These 2 lines are required to bypass self signed certificate errors, at least on my machine
# these things can be finicky depending on your system setup
client.tls_set(tls_version=ssl.PROTOCOL_TLS, cert_reqs=ssl.CERT_NONE)
# client.tls_set_context(create_local_ssl_context())
client.tls_insecure_set(True)


client.connect(BAMBU_IP_ADDRESS, 8883, 60)


client.publish(f"device/{SERIAL}/request", '{"pushing": {"command": "start", "sequence_id": 0}}')
# client.publish(f"device/{SERIAL}/report", '{"pushing": {"command": "start", "sequence_id": 0}}')
# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
