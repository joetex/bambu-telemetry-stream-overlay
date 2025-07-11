from flask import Flask, render_template
from flask_sock import Sock
import webbrowser

from datetime import datetime, timedelta
from pathlib import Path
import json

import tkinter as tk
from threading import Thread
import bambu

import os
import sys

templatesDir = os.getcwd() + '/templates'
staticDir = os.getcwd() + '/static'

app = Flask(__name__, static_folder=staticDir)
sock = Sock(app)

prevTelemetry = {}
fields = {}
rowId = 2
clients = set()
mqtt_client = None


@app.route('/')
def home():
    # return render_template('overlay.html')
    return app.send_static_file('overlay.html')


@app.route('/telemetry')
def config():
    # This route can be used to serve configuration data if needed
    # return render_template('telemetry.html')
    return app.send_static_file('telemetry.html')


@sock.route('/bambu')
def echo(ws):
    print("Client connected to /bambu")
    clients.add(ws)
    try:

        if( mqtt_client is not None):
            print("MQTT client is connected, sending initial telemetry data")
            # Send initial telemetry data if available
            send_to_client(ws, "status", "connected")
            
            send_to_clients("telemetry", prevTelemetry)  # Send previous telemetry data to clients
        while True:
            data = ws.receive()  # Receive message from the client
            if data:
                print(f"Received from client: {data}")
                ws.send(f"Echo: {data}")  # Send message back to the client
            else:
                # Handle client disconnection or empty message
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        clients.discard(ws)
        print("Client disconnected from /echo!")


def run_flask_app():
    # if __name__ == '__main__':
        # app.run(debug=True)
    # else :
    app.run(debug=False) # Set debug to False for production
    
def open_browser_overlay():
    webbrowser.open('http://127.0.0.1:5000/', new=0, autoraise=True)

def open_browser_telemetry():
    webbrowser.open('http://127.0.0.1:5000/telemetry', new=0, autoraise=True)


def send_to_client(client, type, data):  
    """Send data to a specific WebSocket client."""
    try:
        client.send(json.dumps({"type":type, "payload":data}))  # Convert data to JSON string before sending
    except Exception as e:
        print(f"Error sending data to client: {e}")

def send_to_clients(type, data):  
    """Send data to all connected WebSocket clients."""
    for client in clients:
        try:
            client.send(json.dumps({"type":type, "payload":data}))  # Convert data to JSON string before sending
        except Exception as e:
            print(f"Error sending data to client: {e}")


def on_bambu_telemetry(telementry_data):
    global prevTelemetry
    print("Received telemetry data from Bambu printer:", telementry_data)
    prevTelemetry = { **prevTelemetry, **telementry_data }
    send_to_clients("telemetry", telementry_data)

def on_bambu_connect(client, userdata, flags, rc):
    print("Connected to Bambu printer with result code:", rc)
    fields['connect_button'].config(text="Disconnect from Bambu Printer")  # Disable the connect button after successful connection
    fields['connect_button'].config(state=tk.ACTIVE)
    send_to_clients("status", "connected")


def on_bambu_disconnect(client, userdata, rc):
    print("Disconnected from Bambu printer with result code:", rc)
    fields['connect_button'].config(text="Connect to Bambu Printer")  # Re-enable the connect button after disconnection
    fields['connect_button'].config(state=tk.ACTIVE)
    send_to_clients("status", "disconnected")
    global mqtt_client
    mqtt_client = None  # Reset the MQTT client reference
    

def start_flask_thread():
    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True  # Allows the thread to exit when the main program exits
    flask_thread.start()


def start_bambu_thread():
    flask_thread = Thread(target=connect_bambu)
    flask_thread.daemon = True  # Allows the thread to exit when the main program exits
    flask_thread.start()

def connect_bambu(): 
    global mqtt_client

    if mqtt_client is not None:
        print("MQTT is disconnected.")
        mqtt_client.disconnect()
        fields['connect_button'].config(text="Connect to Bambu Printer")
        send_to_clients("status", "disconnected")
        mqtt_client = None
        return
    
    send_to_clients("status", "connecting...")
    fields['connect_button'].config(text="Connecting to Bambu Printer...")
    fields['connect_button'].config(state=tk.DISABLED)
    credentials = save_entry_value()

    try:
        mqtt_client = bambu.connect_mqtt(credentials, on_bambu_connect, on_bambu_telemetry, on_bambu_disconnect)
    
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"Error connecting to Bambu printer: {e}")
        fields['connect_button'].config(text="Connect to Bambu Printer")
        fields['connect_button'].config(state=tk.ACTIVE)
        send_to_clients("status", "error")
        mqtt_client = None


def save_entry_value():
    """Saves the Entry widget's value to a JSON file."""
    
    credentials = {
        "bambu_ip": fields['bambu_ip']['entry'].get(),  # IP Address
        "serial": fields['serial']['entry'].get(),     # Serial Number  
        "access_code": fields['access_code']['entry'].get(),  # Access Code
        "bambu_port": "8883",
        "username": "bblp"
    }
    try:
        with open("settings.json", "w") as f:
            json.dump(credentials, f, indent=4)
        # status_label.config(text="Value saved successfully!")
    except Exception as e:
        print(f"Error saving settings: {e}")
        # status_label.config(text=f"Error saving: {e}")

    return credentials

def load_entry_value():
    """Loads the Entry widget's value from a JSON file."""
    try:
        with open("settings.json", "r") as f:
            credentials = json.load(f)

            for key in credentials:
                if key in fields:
                    loaded_value = credentials[key]
                    var = tk.StringVar(value=loaded_value)
                    fields[key]['entry'].config(textvariable=var)

            # status_label.config(text="Value loaded successfully!")
    except FileNotFoundError:
        print("Settings file not found.")
        # status_label.config(text="Settings file not found.")
    except Exception as e:
        print(f"Error loading settings: {e}")
        # status_label.config(text=f"Error loading: {e}")



# Tkinter GUI setup
root = tk.Tk()
root.title("Bambu Telemetry Overlay")
root.geometry("800x600") # Set initial window size
root.grid_rowconfigure(0, minsize=20)

def create_field(rowIndex, name, value, text, helpertext):
    label = tk.Label(root, text=text, justify="left", anchor="w")
    label.grid(row=rowIndex, column=0, padx=(10,0), pady=0, sticky="e")
    var = tk.StringVar(value=value)
    entry = tk.Entry(root, textvariable=var, width=30)
    
    entry.grid(row=rowIndex, column=1, padx=0, pady=0, sticky="ew")
    helper = tk.Label(root, text=helpertext,  font=("Arial", 8), fg='#666')
    helper.grid(row=rowIndex+1, column=0, columnspan=2, padx=0, pady=(0,20), sticky="e")
    
    field = {}
    field['label'] = label
    field['entry'] = entry
    field['helper'] = helper
    field['value'] = value
    field['var'] = var
    
    fields[name] = field

    rowIndex = rowIndex + 1
    return fields[name]


# Create labels and entry fields
def create_form():
    header = tk.Label(root, text="Bambu Connection",  font=("Arial", 14), fg='#111')
    header.grid(row=0, column=0, columnspan=2, padx=0, pady=(0,5), sticky="ew")


    create_field(rowId, 'bambu_ip', "192.168.0.1", "Printer IP Address:", "Find IP in Printer Panel WLAN settings")
    # create_field(rowId+2, 'bambu_port', "Port:", "")
    create_field(rowId+4, 'access_code', "", "Access Code:", "Find Access Code in Printer Panel WLAN settings")
    create_field(rowId+6,'serial', "", "Serial Number:", "Find Serial in Printer Panel Device settings under 'Printer'")    

    # Create a submit button
    submit_button = tk.Button(root, text="Connect to Bambu Printer", command=start_bambu_thread)
    submit_button.grid(row=rowId+8, column=0, columnspan=2, padx=0, pady=(0,20), sticky="e")
    fields['connect_button'] = submit_button


    browser_overlay_button = tk.Button(root, text="Open Overlay", command=open_browser_overlay)
    browser_overlay_button.grid(row=rowId+16, column=0,  columnspan=2, padx=0, pady=0, sticky="e")
    fields['browser_overlay_button'] = browser_overlay_button


    browser_telemetry_button = tk.Button(root, text="Open Telemetry", command=open_browser_telemetry)
    browser_telemetry_button.grid(row=rowId+18, column=0, columnspan=2, padx=0, pady=0, sticky="e")
    fields['browser_telemetry_button'] = browser_telemetry_button

    load_entry_value()


start_flask_thread()

create_form()
root.mainloop()