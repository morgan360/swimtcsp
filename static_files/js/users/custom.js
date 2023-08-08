// custom.js
document.addEventListener("DOMContentLoaded", function () {
    // Get the message element
    var messageElement = document.getElementById("message");

    // If the message element exists, set a timeout to hide it after 5 seconds
    if (messageElement) {
        setTimeout(function () {
            messageElement.style.display = "none";
        }, 2000); // Change the value (in milliseconds) to adjust the duration
    }
});
