"""Temporary, tagged CloudFormation stack; no production database is reused."""


def ref(name):
    return {"Ref": name}


def attr(name, field):
    return {"Fn::GetAtt": [name, field]}


def template(engine_version="17.9"):
    resources = {}

    def add(name, kind, **properties):
        resources[name] = {"Type": kind, "Properties": properties}

    add(
        "Vpc",
        "AWS::EC2::VPC",
        CidrBlock="10.87.0.0/16",
        EnableDnsSupport=True,
        EnableDnsHostnames=True,
    )
    for i in range(2):
        add(
            f"Subnet{i}",
            "AWS::EC2::Subnet",
            VpcId=ref("Vpc"),
            CidrBlock=f"10.87.{i}.0/24",
            AvailabilityZone={"Fn::Select": [i, {"Fn::GetAZs": ""}]},
        )
    add(
        "WorkerGroup",
        "AWS::EC2::SecurityGroup",
        GroupDescription="Isolated direct baseline",
        VpcId=ref("Vpc"),
    )
    add(
        "DatabaseGroup",
        "AWS::EC2::SecurityGroup",
        GroupDescription="No public database access",
        VpcId=ref("Vpc"),
        SecurityGroupIngress=[
            dict(
                IpProtocol="tcp",
                FromPort=5432,
                ToPort=5432,
                SourceSecurityGroupId=ref("WorkerGroup"),
            )
        ],
    )
    add(
        "Subnets",
        "AWS::RDS::DBSubnetGroup",
        DBSubnetGroupDescription="Validation only",
        SubnetIds=[ref("Subnet0"), ref("Subnet1")],
    )
    add(
        "Secret",
        "AWS::SecretsManager::Secret",
        GenerateSecretString={
            "SecretStringTemplate": '{"username":"validator"}',
            "GenerateStringKey": "password",
            "PasswordLength": 40,
            "ExcludePunctuation": True,
        },
    )
    secret = {
        "Fn::Join": ["", ["{{resolve:secretsmanager:", ref("Secret"), ":SecretString:password}}"]]
    }
    add(
        "Cluster",
        "AWS::RDS::DBCluster",
        Engine="aurora-postgresql",
        EngineVersion=engine_version,
        DatabaseName="data_api_test",
        MasterUsername="validator",
        MasterUserPassword=secret,
        StorageEncrypted=True,
        EnableHttpEndpoint=True,
        BackupRetentionPeriod=1,
        DBSubnetGroupName=ref("Subnets"),
        VpcSecurityGroupIds=[ref("DatabaseGroup")],
        ServerlessV2ScalingConfiguration={
            "MinCapacity": 0,
            "MaxCapacity": 2,
            "SecondsUntilAutoPause": 300,
        },
    )
    resources["Cluster"]["DeletionPolicy"] = "Delete"
    add(
        "Writer",
        "AWS::RDS::DBInstance",
        DBClusterIdentifier=ref("Cluster"),
        Engine="aurora-postgresql",
        DBInstanceClass="db.serverless",
        PubliclyAccessible=False,
    )
    assume = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    add(
        "ApiRole",
        "AWS::IAM::Role",
        AssumeRolePolicyDocument=assume,
        ManagedPolicyArns=["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
        Policies=[
            {
                "PolicyName": "OnlyExperimentDatabase",
                "PolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "rds-data:ExecuteStatement",
                                "rds-data:BeginTransaction",
                                "rds-data:CommitTransaction",
                                "rds-data:RollbackTransaction",
                            ],
                            "Resource": attr("Cluster", "DBClusterArn"),
                        },
                        {
                            "Effect": "Allow",
                            "Action": "secretsmanager:GetSecretValue",
                            "Resource": ref("Secret"),
                        },
                    ],
                },
            }
        ],
    )
    add(
        "BaselineRole",
        "AWS::IAM::Role",
        AssumeRolePolicyDocument=assume,
        ManagedPolicyArns=["arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"],
    )
    common = dict(
        Runtime="python3.12",
        Handler="index.handler",
        Timeout=300,
        MemorySize=1024,
        Architectures=["x86_64"],
        Code={
            "ZipFile": (
                "def handler(event, context):\n"
                "    raise RuntimeError('Upload validation package first')\n"
            )
        },
    )
    add(
        "Api",
        "AWS::Lambda::Function",
        **common,
        Role=attr("ApiRole", "Arn"),
        Environment={
            "Variables": {
                "CLUSTER_ARN": attr("Cluster", "DBClusterArn"),
                "SECRET_ARN": ref("Secret"),
            }
        },
    )
    add(
        "Baseline",
        "AWS::Lambda::Function",
        **common,
        Role=attr("BaselineRole", "Arn"),
        VpcConfig={"SubnetIds": [ref("Subnet0")], "SecurityGroupIds": [ref("WorkerGroup")]},
        Environment={
            "Variables": {"DB_HOST": attr("Cluster", "Endpoint.Address"), "DB_PASSWORD": secret}
        },
    )
    resources["Baseline"]["DependsOn"] = "Writer"
    # Explicit log resources disappear with the stack; no orphaned CloudWatch groups.
    for name in ("Api", "Baseline"):
        add(
            name + "Logs",
            "AWS::Logs::LogGroup",
            RetentionInDays=1,
            LogGroupName={"Fn::Join": ["", ["/aws/lambda/", ref(name)]]},
        )
    add(
        "Artifacts",
        "AWS::S3::Bucket",
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True,
        },
        BucketEncryption={
            "ServerSideEncryptionConfiguration": [
                {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
            ]
        },
    )
    outputs = {
        k: {"Value": v}
        for k, v in {
            "ClusterArn": attr("Cluster", "DBClusterArn"),
            "ClusterId": ref("Cluster"),
            "SecretArn": ref("Secret"),
            "Api": ref("Api"),
            "Baseline": ref("Baseline"),
            "Artifacts": ref("Artifacts"),
            "WriterId": ref("Writer"),
        }.items()
    }
    return {"AWSTemplateFormatVersion": "2010-09-09", "Resources": resources, "Outputs": outputs}
