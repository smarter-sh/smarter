function handler(event) {
  var request = event.request;
  var uri = request.uri;

  // Match exactly "/en/latest" or anything underneath it
  if (uri === "/en/latest" || uri.startsWith("/en/latest/")) {
    // Remove the prefix
    var newUri = uri.substring("/en/latest".length);

    // Ensure we don't end up with an empty path
    if (newUri === "") {
      newUri = "/";
    }
    return {
      statusCode: 301,
      statusDescription: "Moved Permanently",
      headers: {
        location: {
          value: "https://docs.smarter.sh" + newUri,
        },
      },
    };
  }
  return request;
}
