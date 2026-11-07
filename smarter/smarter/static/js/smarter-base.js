
function getSmarterCsrfToken() {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return csrftoken;
}

/**
 * Sign out with the console's account api, from a form with a data-smarter-sign-out attribute, e.g. the docs
 * pages' Logout item: POST to the form's action with its CSRF token, then go to the attribute's url, the sign-in
 * page. See templates/cms/base/menu/authentication.html.
 */
document.addEventListener("submit", function (event) {
    const form = event.target.closest("form[data-smarter-sign-out]");
    if (!form) return;
    event.preventDefault();
    const token = form.querySelector("[name=csrfmiddlewaretoken]").value;
    fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": token, "Content-Type": "application/json" },
        body: "{}",
        credentials: "same-origin",
    }).then(function () {
        window.location.assign(form.dataset.smarterSignOut);
    });
});
