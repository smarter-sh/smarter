"""AWS DynamoDB helper class."""

import logging
from typing import Optional

from .aws import AWSBase

logger = logging.getLogger(__name__)


class AWSDynamoDB(AWSBase):
    """AWS DynamoDB helper class."""

    _client = None
    _client_type: str = "dynamodb"

    def get_dyanmodb_table_by_name(self, table_name) -> Optional[str]:
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
