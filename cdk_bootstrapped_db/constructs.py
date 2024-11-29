import json
import os
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
    password, optionally a read-only user if `read_only_username` is provided.
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
        read_only_username: Optional[str] = None,
    ) -> None:
        super().__init__(scope, id)

        if not db.secret:
            raise ValueError("`db` value must have a secret attached.")

        if not db.engine and not db_engine:
            raise ValueError(
                "Either the provided `db` must have access to its `engine` property or"
                " you must provide a value for `db_engine` explicitly."
            )

        # Create secret for the main user
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
                        "engine": db_engine
                        if db_engine
                        else db.engine.engine_type,  # type: ignore
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

        # Optionally create a secret for the read-only user
        self.read_only_secret = None
        if read_only_username:
            self.read_only_secret = secretsmanager.Secret(
                self,
                f"{id}-readonly-secret",
                secret_name=os.path.join(
                    secrets_prefix,
                    f"{id}_readonly".replace(" ", "_"),
                    self.node.id[-8:],
                ),
                generate_secret_string=secretsmanager.SecretStringGenerator(
                    secret_string_template=json.dumps(
                        {
                            "dbname": new_dbname,
                            "engine": db_engine
                            if db_engine
                            else db.engine.engine_type,  # type: ignore
                            "port": db.instance_endpoint.port,
                            "host": db.instance_endpoint.hostname,
                            "username": read_only_username,
                        },
                    ),
                    generate_string_key="password",
                    exclude_punctuation=True,
                ),
                description=f"Read-only user secret deployed by {Stack.of(self).stack_name}",  # noqa: E501
            )

        self.provider = custom_resources.Provider(
            scope, "BootstrapProvider", on_event_handler=handler
        )

        # Prepare the properties for the custom resource
        resource_properties = {
            "conn_secret_arn": db.secret.secret_arn,
            "new_user_secret_arn": self.secret.secret_arn,
            "version": handler.current_version.version,
        }

        # Optionally include the read-only secret ARN
        if self.read_only_secret:
            resource_properties[
                "read_only_user_secret_arn"
            ] = self.read_only_secret.secret_arn

        self.resource = CustomResource(
            scope=scope,
            id="BootstrapHandlerResource",
            service_token=self.provider.service_token,
            properties=resource_properties,
        )

        # Grant the Lambda handler permissions to read the main user secret
        self.secret.grant_read(handler)

        # If the read-only secret exists, grant the handler permissions to read it
        if self.read_only_secret:
            self.read_only_secret.grant_read(handler)

        # Grant the Lambda handler permission to connect to the database
        db.secret.grant_read(handler)
        db.connections.allow_from(handler, port_range=ec2.Port.tcp(5432))

    def is_required_by(self, construct: Construct):
        return construct.node.add_dependency(self.resource)
