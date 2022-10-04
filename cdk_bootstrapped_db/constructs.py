import json
import os
from datetime import datetime
from typing import Optional, Union

from aws_cdk import (
    aws_lambda,
    aws_secretsmanager as secretsmanager,
    aws_rds as rds,
    aws_ec2 as ec2,
    Stack,
    CustomResource,
    custom_resources,
)

from constructs import Construct


class BootstrappedDb(Construct):
    """
    Given an RDS database, connect to DB and create a database, user, and
    password
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        db: Union[rds.DatabaseInstance, rds.DatabaseInstanceFromSnapshot],
        new_dbname: str,
        new_username: str,
        secrets_prefix: str,
        handler: Union[aws_lambda.Function, aws_lambda.SingletonFunction],
        db_engine: Optional[str] = None,
    ) -> None:
        super().__init__(scope, id)

        if not db.secret:
            raise ValueError("`db` value must have a secret attached.")

        if not db.engine and not db_engine:
            raise ValueError(
                "Either the provided `db` must have access to its `engine` property or"
                " you must provide a value for `db_engine` explicitly."
            )

        self.secret = secretsmanager.Secret(
            self,
            id,
            secret_name=os.path.join(
                secrets_prefix, id.replace(" ", "_"), self.node.id[-8:]
            ),
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        "dbname": new_dbname,
                        "engine": db_engine if db_engine else db.engine.engine_type,  # type: ignore
                        "port": db.instance_endpoint.port,
                        "host": db.instance_endpoint.hostname,
                        "username": new_username,
                    },
                ),
                generate_string_key="password",
                exclude_punctuation=True,
            ),
            description=f"Deployed by {Stack.of(self).stack_name}",
        )

        self.provider = custom_resources.Provider(
            scope, "BootstrapProvider", on_event_handler=handler
        )

        self.resource = CustomResource(
            scope=scope,
            id="BootstrapHandlerResource",
            service_token=self.provider.service_token,
            properties={
                "conn_secret_arn": db.secret.secret_arn,
                "new_user_secret_arn": self.secret.secret_arn,
                "version": handler.current_version.version,
            },
        )

        # Allow lambda to...
        # read new user secret
        self.secret.grant_read(handler)
        # read database secret
        db.secret.grant_read(handler)
        # connect to database
        db.connections.allow_from(handler, port_range=ec2.Port.tcp(5432))

    def is_required_by(self, construct: Construct):
        return construct.node.add_dependency(self.resource)
