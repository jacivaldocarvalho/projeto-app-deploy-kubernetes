$("#contact").on("submit", function(event) {
    event.preventDefault();
    var form = this;
    var button = $("#button-blue");
    button.prop("disabled", true);
    $.ajax({
        url: form.action,
        type: "post",
        data: $(form).serialize(),
        timeout: 10000
    }).done(function() {
        alert("Message saved successfully");
        form.reset();
    }).fail(function(response) {
        if (response.status === 422) {
            alert(response.responseText);
        } else {
            alert("Unable to save the message. Please try again later.");
        }
    }).always(function() {
        button.prop("disabled", false);
    });
});
