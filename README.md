## Bambu Telemetry Stream Overlay

A work in progress to simplify using a Browser Source in OBS to render bambu 3d printer telemetry.  

The Python application uses a simple UI to connect to your Bambu Printer (P, X, H) series using MQTT protocol.  It automatically starts a local web server to host `overlay.html` and `telemetry.html` files to customize the experience.  

The Telemetry data on the bottom left of the preview screen is customizable in `static/overlay.html`, `static/overlay.css` and `static/overlay.js`

<img width="1608" height="1079" alt="image" src="https://github.com/user-attachments/assets/768e4457-b977-4926-be80-0653808ca024" />


<img width="250" height="260" alt="image" src="https://github.com/user-attachments/assets/1d446868-d051-4054-a9a2-9240de308afe" />



### Install using Source Code

```
pip install -r /path/to/requirements.txt
```

### Or, Install using Binary

1. Unzip the `bambu_telemetry_stream_overaly.0.0.2.zip` to your filesystem.
2. Navigate to the folder and find the `app.exe` file.

### How to run the code

```
python app.py
```

## Customization

All the telemetry data is passed through websockets from the local web server to the `overlay.js` and `telemetry.js` files.  You can use the existing examples to modify the HTML/CSS files to change the look and feel of the UI.

## OBS Browser Sources
Should work with any streaming app, just pass the URL below into the Browser Source.

#### Overlay
http://127.0.0.1:5000/
The live feed of customized telemetry experience.

#### Telemetry
http://127.0.0.1:5000/telemetry
The live feed of raw JSON output in a format that can be viewed.
