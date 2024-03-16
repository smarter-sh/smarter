
function getSmarterCsrfToken() {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    return csrftoken;
}
