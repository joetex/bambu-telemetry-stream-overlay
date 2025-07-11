var ws = new WebSocket("ws://" + location.host + "/bambu");

ws.onmessage = function (event) {
    let msg = JSON.parse(event.data);
    let type = msg.type;
    let data = msg.payload;

    if (type == "telemetry") {
        var messagesDiv = document.getElementById("telemetry");
        messagesDiv.innerHTML = "<pre>" + JSON.stringify(data, null, 2) + "</pre>";
        console.log("Received: " + data);
    } else if (type == "status") {
        var statusDiv = document.getElementById("status");
        statusDiv.innerHTML = data;
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
