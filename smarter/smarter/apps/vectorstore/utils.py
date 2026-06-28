from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.const import PINECONE_API_KEY_SECRET_NAME


def get_pinecone_api_key() -> str | None:
    """
    Retrieve the Pinecone API key from the Secret model.

    Returns:
        str: The Pinecone API key.
    """
    try:
        secret = Secret.objects.get(name=PINECONE_API_KEY_SECRET_NAME)
    except Secret.DoesNotExist:
        return None
    secret_string = secret.get_secret()
    if not secret_string or secret_string == "":
        return None
    return secret_string
