# -*- coding: utf-8 -*-
"""AWS DynamoDB helper class."""

from .aws import AWSBase


class AWSDynamoDB(AWSBase):
    """AWS DynamoDB helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS DynamoDB client."""
        if not self._client:
            self._client = self.aws_session.client("dynamodb")
        return self._client

    def get_dyanmodb_table_by_name(self, table_name) -> str:
        """Return the DynamoDB table given the table name."""
        response = self.client.list_tables()
        for table in response["TableNames"]:
            if table == table_name:
                table_description = self.client.describe_table(TableName=table_name)
                return table_description["Table"]["TableArn"]
        return None

    def dynamodb_table_exists(self, table_name) -> bool:
        """Test that the DynamoDB table exists."""
        table = self.get_dyanmodb_table_by_name(table_name)
        return table is not None
