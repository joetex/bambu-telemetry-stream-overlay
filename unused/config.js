var ws = new WebSocket("ws://" + location.host + "/wsconfig");

ws.onmessage = function (event) {
    var messagesDiv = document.getElementById("telemetry");
    messagesDiv.innerHTML += "<p>Received: " + event.data + "</p>";
    console.log("Received: " + event.data);
};

function sendMessage() {
    var input = document.getElementById("messageInput");
    var message = input.value;
    ws.send(message);
    input.value = "";
}

let action_connect = document.getElementsByClassName("action_connect")[0];

if (action_connect) {
    action_connect.addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent the default form submission
    });

    action_connect.addEventListener("click", function (event) {
        var access_code = document.getElementById("access_code").value;
        var bambu_ip = document.getElementById("bambu_ip").value;
        var serial = document.getElementById("serial").value;
        var username = document.getElementById("serial").value;
        var bambu_port = document.getElementById("bambu_port").value;

        if (access_code && bambu_ip && serial && username && bambu_port) {
            ws.send(
                JSON.stringify({
                    command: "connect",
                    access_code,
                    bambu_ip,
                    username,
                    bambu_port,
                    serial,
                })
            );
        } else {
            alert("Please fill in all fields.");
        }
    });
}
