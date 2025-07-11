var ws = new WebSocket("ws://" + location.host + "/bambu");

ws.onmessage = function (event) {
    let msg = JSON.parse(event.data);
    let type = msg.type;
    let data = msg.payload;

    if (type == "telemetry") {
        // var messagesDiv = document.getElementById("telemetry");
        // messagesDiv.innerHTML = "<pre>" + JSON.stringify(data, null, 2) + "</pre>";
        let layer = data["layer_num"] || 0;
        let total_layers = data["total_layer_num"] || 0;
        let speed = data["spd_lvl"] || 2;
        let speed_map = { 1: "Silent", 2: "Standard", 3: "Sport", 4: "Ludacris" };
        let min_remain = data["mc_remaining_time"];

        let nozzle_temp = (parseFloat(data["nozzle_temper"] || 0) * 9.0) / 5.0 + 32; // Convert to Fahrenheit
        let nozzle_target_temp =
            data["nozzle_target_temper"] != "0"
                ? (parseFloat(data["nozzle_target_temper"]) * 9.0) / 5.0 + 32
                : "--"; // Convert to Fahrenheit

        let bed_temp = (parseFloat(data["bed_temper"]) * 9.0) / 5.0 + 32; // Convert to Fahrenheit
        let bed_target_temp =
            data["bed_target_temper"] != "0"
                ? (parseFloat(data["bed_target_temper"]) * 9.0) / 5.0 + 32
                : "--"; // Convert to Fahrenheit

        let layer_elem = document.getElementById("print_layer");
        let nozzle_temp_elem = document.getElementById("nozzle_temp");
        let bed_temp_elem = document.getElementById("bed_temp");
        let finish_eta_elem = document.getElementById("finish_time");
        let speed_elem = document.getElementById("print_speed");
        // let future_time = Date.now() + timedelta(minutes=min_remain)
        //     future_time_str = future_time.strftime("%Y-%m-%d %H:%M")

        layer_elem.innerText = `${layer} of ${total_layers} (${data["mc_percent"]} %)`;
        nozzle_temp_elem.innerText = `${parseInt(nozzle_temp)} / ${nozzle_target_temp} F°`;
        bed_temp_elem.innerText = `${parseInt(bed_temp)} / ${bed_target_temp} F°`;
        finish_eta_elem.innerText = new Date(Date.now() + min_remain * 60000)
            .toISOString()
            .slice(0, 19)
            .replace("T", " ");
        speed_elem.innerText = speed_map[speed];

        active_ams = data["ams"]["tray_now"];

        try {
            for (tray in data["ams"]["ams"][0]["tray"]) {
                let tray_remain = "";
                let color_name = tray["cols"][0]; // rgb_to_color_name(tray['cols'][0])
                if (active_ams == tray["id"]) active = " - In Use";
                else active = "";
                if (tray["remain"] != -1) tray_remain = `(${tray["remain"]}% remain)`;
                if (tray["tray_sub_brands"] == "") tray_type = tray["tray_type"];
                else tray_type = tray["tray_sub_brands"];
                // fp.write(f"Tray {tray['id']}: {tray_type} {color_name} {tray_remain}  {active}\n")

                if (active_ams == "254") active = " - In Use";
                else active = "";

                // color_name = rgb_to_color_name(values['vt_tray']['cols'][0])

                // fp.write(f"Ext. : {values['vt_tray']['tray_type']} {color_name} {active}")
            }
        } catch (e) {}

        console.log("Received: " + data);
    } else if (type == "status") {
        // var statusDiv = document.getElementById("status");
        // statusDiv.innerHTML = data;
        console.log("Status: " + data);
    } else {
        console.warn("Unknown message type: " + type);
    }
};

function sendMessage() {
    var input = document.getElementById("messageInput");
    var message = input.value;
    ws.send(message);
    input.value = "";
}
