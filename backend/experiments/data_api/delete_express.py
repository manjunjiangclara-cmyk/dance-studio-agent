"""Delete only a tagged validation cluster without producing a final snapshot."""

import argparse
import re
import time


def delete(client, name):
    if not re.fullmatch(r"data-api-validation-[a-f0-9]{12}", name):
        raise ValueError("Refusing a database outside the validation namespace.")
    try:
        cluster = client.describe_db_clusters(DBClusterIdentifier=name)["DBClusters"][0]
    except Exception as error:
        if getattr(error, "response", {}).get("Error", {}).get("Code") == "DBClusterNotFoundFault":
            return
        raise
    tags = {
        t["Key"]: t["Value"]
        for t in client.list_tags_for_resource(ResourceName=cluster["DBClusterArn"])["TagList"]
    }
    if tags.get("Project") != "dance-studio-agent" or tags.get("Purpose") != "data-api-validation":
        raise ValueError("Refusing a database without both validation ownership tags.")

    def code(error):
        return getattr(error, "response", {}).get("Error", {}).get("Code")

    for _ in range(60):
        if cluster["Status"] != "deleting":
            members = [
                member["DBInstanceIdentifier"] for member in cluster.get("DBClusterMembers", [])
            ]
            # Validate every member before deleting any of them.
            if any(not instance.startswith(name + "-") for instance in members):
                raise ValueError("Refusing a writer outside the exact validation cluster prefix.")
            for instance in members:
                try:
                    info = client.describe_db_instances(DBInstanceIdentifier=instance)[
                        "DBInstances"
                    ][0]
                    if info["DBInstanceStatus"] != "deleting":
                        client.delete_db_instance(
                            DBInstanceIdentifier=instance, SkipFinalSnapshot=True
                        )
                except Exception as error:
                    if code(error) != "DBInstanceNotFound":
                        raise
            try:
                client.delete_db_cluster(DBClusterIdentifier=name, SkipFinalSnapshot=True)
            except Exception as error:
                if code(error) == "DBClusterNotFoundFault":
                    return
                if code(error) != "InvalidDBClusterStateFault":
                    raise
        try:
            cluster = client.describe_db_clusters(DBClusterIdentifier=name)["DBClusters"][0]
        except Exception as error:
            if code(error) == "DBClusterNotFoundFault":
                return
            raise
        print("Waiting for validation Express deletion without a final snapshot.", flush=True)
        time.sleep(10)
    raise TimeoutError("Validation cluster deletion did not finish within ten minutes.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"arn:aws:iam::\d{12}:role/dance-studio-deployer", args.role):
        parser.error("Use the approved project deployment role.")
    cleanup(args.role, args.name)


def cleanup(role, name):
    import boto3

    credentials = boto3.client("sts").assume_role(
        RoleArn=role, RoleSessionName="validation-cleanup"
    )["Credentials"]
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name="ap-southeast-2",
    )
    delete(session.client("rds"), name)


if __name__ == "__main__":
    main()
