# CDK Bootstrapped DB Construct

This CDK Construct enables provisioning an RDS Database (and optionally a DB Server) with a bootstrapping Lambda function for running migrations other setup requirements.

## Usage

```python
import os
from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda as lambda_,
)

from constructs import Construct

from cdk_bootstrapped_db.constructs import BootstrappedDb


class MyDatabase(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
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

### Creating an RDS Server from a Snapshot

If you have a snapshot of an RDS Server that you wish to restore in a new deployment, you can pass in the optional parameter
`db_snapshot_arn` to `create_database_server` instead of using `db_name`.

This snapshot must reside in the region you're deploying into, you can copy a snapshot across regions following these docs:
https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CopySnapshot.html

By default, the created server will use the admin username of `postgres` - If the RDS Server your snapshot is from used a
different admin username, you can provide it with the parameter `db_snapshot_admin_username`.

This whole scenario is shown below:

```python
import os
from aws_cdk import (
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
            db_snapshot_arn="arn:aws:rds:us-west-2:123456789012:snapshot:mysql-instance1-snapshot-20130805",
            db_snapshot_admin_username="myadminusername",
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
