from typing import Optional, Union

from aws_cdk import aws_ec2 as ec2, aws_rds as rds, Stack, RemovalPolicy

from constructs import Construct


def create_database_server(
    scope: Construct,
    id: str,
    vpc: ec2.IVpc,
    subnet_selection: ec2.SubnetSelection,
    deletion_protect: bool,
    db_name: Optional[str] = None,
    db_snapshot_arn: Optional[str] = None,
    db_version: Optional[rds.PostgresEngineVersion] = None,
    identifier: Optional[str] = None,
    **kwargs,
) -> Union[rds.DatabaseInstance, rds.DatabaseInstanceFromSnapshot]:
    assert (
        db_snapshot_arn or db_name
    ), "Must provide either 'db_snapshot_arn' or 'db_name'"

    engine = (
        rds.DatabaseInstanceEngine.postgres(version=db_version)
        if db_version
        else rds.DatabaseInstanceEngine.POSTGRES
    )

    params = {
        "id": id,
        "scope": scope,
        "vpc": vpc,
        "engine": engine,
        "instance_type": ec2.InstanceType.of(
            ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL
        ),
        "instance_identifier": "-".join(
            [v for v in [Stack.of(scope).stack_name, identifier] if v]
        ),
        "vpc_subnets": subnet_selection,
        "deletion_protection": deletion_protect,
        "removal_policy": (
            RemovalPolicy.SNAPSHOT if deletion_protect else RemovalPolicy.DESTROY
        ),
        **kwargs,
    }

    if db_snapshot_arn:
        return rds.DatabaseInstanceFromSnapshot(
            **params,
            snapshot_identifier=db_snapshot_arn,
            credentials=rds.SnapshotCredentials.from_generated_password(
                # Default admin username for Postgres is "postgres" for rds.DatabaseInstance
                # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_rds/DatabaseInstance.html#aws_cdk.aws_rds.DatabaseInstance
                username="postgres"
            ),
        )

    return rds.DatabaseInstance(database_name=db_name, **params)
