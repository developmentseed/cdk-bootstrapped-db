# CDK Bootstrapped DB Construct

This CDK Construct enables provisioning an RDS Database (and optionally a DB Server) with a bootstrapping Lambda function for running migrations other setup requirements.

## Usage

```python
import os
from aws_cdk import (
    Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda as lambda_,
)

from constructs import Construct

from cdk_bootstrapped_db.helpers import create_database_server
from cdk_bootstrapped_db.constructs import BootstrappedDb


class MyDatabase(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        name: str,
        secrets_prefix: str,
        db_server: rds.DatabaseInstance,
        vpc: ec2.IVpc,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        db_setup_handler = lambda_.Function(
            self,
            "RunMigrations",
            handler="handler.handler",
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_docker_build(
                path=os.path.abspath("."),
                file="Dockerfile",
            ),
            vpc=vpc,
        )

        self.db = BootstrappedDb(
            self,
            "MyDB",
            db=db_server,
            new_dbname="mydb",
            new_username="mydbuser",
            secrets_prefix=secrets_prefix,
            handler=db_setup_handler,
        )

        self.db_connection_secret = self.db.secret
```

Any external constructs which then need to access the DB using the generated credentials can do so using the `db_connection_secret` property of the `MyDatabase` construct.

### Creating an RDS Server

This package comes with a helper function for setting up a new RDS server. The above example then becomes:

```python
import os
from aws_cdk import (
    Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda as lambda_,
)

from constructs import Construct

from cdk_bootstrapped_db.helpers import create_database_server
from cdk_bootstrapped_db.constructs import BootstrappedDb


class MyDatabase(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        name: str,
        secrets_prefix: str,
        vpc: ec2.IVpc,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        self.db_server = create_database_server(
            self,
            "MyDBServer",
            identifier="mydbserver",
            vpc=vpc,
            db_name="postgres",
            db_version=rds.PostgresEngineVersion.VER_14,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.NANO
            ),
        )

        db_setup_handler = lambda_.Function(
            self,
            "RunMigrations",
            handler="handler.handler",
            runtime=lambda_.Runtime.PYTHON_3_8,
            code=lambda_.Code.from_docker_build(
                path=os.path.abspath("."),
                file="Dockerfile",
            ),
            vpc=vpc,
        )

        self.db = BootstrappedDb(
            self,
            "MyDB",
            db=self.db_server,
            new_dbname="mydb",
            new_username="mydbuser",
            secrets_prefix=secrets_prefix,
            handler=db_setup_handler,
        )

        self.db_connection_secret = self.db.secret
```
