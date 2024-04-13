"""AWS API Gateway helper class."""

from .aws import AWSBase


class AWSAPIGateway(AWSBase):
    """AWS API Gateway helper class."""

    _client = None
    _name = None

    def __init__(self, name=None):
        """Initialize the AWS API Gateway helper class."""
        super().__init__()
        self._name = name

    @property
    def client(self):
        """Return the AWS API Gateway client."""
        if not self._client:
            self._client = self.client
        return self._client

    @property
    def name(self):
        """Return the AWS API Gateway name."""
        return self._name

    @property
    def shared_resource_identifier(self):
        """Return the shared resource identifier."""
        return self._shared_resource_identifier

    def get_api_stage(self) -> str:
        """Return the API stage."""
        api = self.get_api(self.name) or {}
        api_id = api.get("id")
        if api_id:
            response = self.client.get_stages(restApiId=api_id)
            # Assuming you want the most recently deployed stage
            stages = response.get("item", [])
            if stages:
                retval = stages[-1]["stageName"]
                return retval
        return ""

    def get_api_custom_domains(self) -> list:
        """Return the API custom domains."""

        def filter_dicts(lst):
            return [d for d in lst if "domainName" in d and self.shared_resource_identifier in d["domainName"]]

        response = self.client.get_domain_names()
        retval = response.get("items", [])
        return filter_dicts(retval)

    @property
    def api_gateway_name(self):
        """Return the API Gateway name."""
        return self.shared_resource_identifier + "-api"

    def api_exists(self, api_name: str) -> bool:
        """Test that the API Gateway exists."""
        response = self.client.get_rest_apis()

        for item in response["items"]:
            if item["name"] == api_name:
                return True
        return False

    def get_api(self, api_name: str) -> dict:
        """Test that the API Gateway exists."""
        response = self.client.get_rest_apis()

        for item in response["items"]:
            if item["name"] == api_name:
                return item
        return {}

    def api_resource_and_method_exists(self, path, method) -> bool:
        """Test that the API Gateway resource and method exists."""
        api = self.get_api(self.name) or {}
        api_id = api.get("id")
        resources = self.client.get_resources(restApiId=api_id)
        for resource in resources["items"]:
            if resource["path"] == path:
                try:
                    self.client.get_method(restApiId=api_id, resourceId=resource["id"], httpMethod=method)
                    return True
                except self.client.exceptions.NotFoundException:
                    return False

        return False

    def get_api_keys(self) -> str:
        """Test that the API Gateway exists."""
        response = self.client.get_api_keys(includeValues=True)
        for item in response["items"]:
            if item["name"] == self.shared_resource_identifier:
                return item["value"]
        return False
