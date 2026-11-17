terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
provider "aws" { region = "ap-southeast-2" }
data "aws_caller_identity" "current" {}
variable "ubuntu_ami_id" {
  type    = string
  default = "ami-081307e05c61a3854"
  validation {
    condition     = can(regex("^ami-[a-f0-9]{17}$", var.ubuntu_ami_id))
    error_message = "Use the verified Canonical Ubuntu 24.04 amd64 image in Sydney."
  }
}
data "aws_iam_role" "deployer" { name = "dance-studio-deployer" }
locals {
  account = data.aws_caller_identity.current.account_id
  ec2     = "arn:aws:ec2:ap-southeast-2:${local.account}"
  bucket  = "dance-studio-demo-${local.account}-ap-southeast-2"
  state   = "dance-studio-ec2-state-${local.account}"
  tags    = { Project = "dance-studio-agent", Environment = "demo", Purpose = "ec2-application" }
}
resource "aws_iam_role" "runtime" {
  name = "dance-studio-ec2-runtime"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole"
  }] })
  tags = local.tags
}
resource "aws_iam_instance_profile" "runtime" {
  name = aws_iam_role.runtime.name
  role = aws_iam_role.runtime.name
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.runtime.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "runtime" {
  name = "ec2-application-data"
  role = aws_iam_role.runtime.name
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = "secretsmanager:GetSecretValue", Resource = "arn:aws:secretsmanager:ap-southeast-2:${local.account}:secret:dance-studio-demo/application-*" },
    { Effect = "Allow", Action = "s3:GetObject", Resource = "arn:aws:s3:::${local.bucket}/releases/*" },
    { Effect = "Allow", Action = "s3:PutObject", Resource = "arn:aws:s3:::${local.bucket}/backups/*" }
  ] })
}
resource "aws_s3_bucket" "state" {
  bucket        = local.state
  force_destroy = false
  tags          = local.tags
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.state.arn, "arn:aws:s3:::${local.state}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } }
  }] })
}
locals {
  deployment_statements = [
    { Sid = "ReadRegionalInfrastructure", Effect = "Allow", Action = ["ec2:Describe*", "ssm:DescribeInstanceInformation", "ssm:GetCommandInvocation", "ssm:ListCommandInvocations", "ssm:ListCommands"], Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2" } } },
    { Sid = "ReadUbuntuAmi", Effect = "Allow", Action = "ssm:GetParameter", Resource = "arn:aws:ssm:ap-southeast-2::parameter/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id" },
    { Sid = "CreateTaggedResources", Effect = "Allow", Action = ["ec2:CreateVpc", "ec2:CreateSubnet", "ec2:CreateRouteTable", "ec2:CreateInternetGateway", "ec2:CreateSecurityGroup", "ec2:AllocateAddress", "ec2:CreateVolume"], Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2", "aws:RequestTag/Project" = "dance-studio-agent", "aws:RequestTag/Purpose" = "ec2-application", "aws:RequestTag/Environment" = "demo" } } },
    { Sid = "CreateInOwnedVpc", Effect = "Allow", Action = ["ec2:CreateSubnet", "ec2:CreateRouteTable", "ec2:CreateSecurityGroup"], Resource = "${local.ec2}:vpc/*", Condition = { StringEquals = { "aws:ResourceTag/Project" = "dance-studio-agent", "aws:ResourceTag/Purpose" = "ec2-application" } } },
    { Sid = "LaunchTaggedInstanceAndDisk", Effect = "Allow", Action = "ec2:RunInstances", Resource = ["${local.ec2}:instance/*", "${local.ec2}:volume/*"], Condition = { StringEquals = { "aws:RequestTag/Project" = "dance-studio-agent", "aws:RequestTag/Purpose" = "ec2-application" } } },
    { Sid = "CreateOwnedFirewallRules", Effect = "Allow", Action = ["ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress"], Resource = "${local.ec2}:security-group-rule/*", Condition = { StringEquals = { "aws:RequestTag/Project" = "dance-studio-agent", "aws:RequestTag/Purpose" = "ec2-application" } } },
    { Sid = "LaunchUbuntuImage", Effect = "Allow", Action = "ec2:RunInstances", Resource = "arn:aws:ec2:ap-southeast-2::image/${var.ubuntu_ami_id}" },
    { Sid = "LaunchWithOwnedNetwork", Effect = "Allow", Action = "ec2:RunInstances", Resource = ["${local.ec2}:subnet/*", "${local.ec2}:security-group/*"], Condition = { StringEquals = { "aws:ResourceTag/Project" = "dance-studio-agent", "aws:ResourceTag/Purpose" = "ec2-application" } } },
    { Sid = "LaunchNetworkInterface", Effect = "Allow", Action = "ec2:RunInstances", Resource = "${local.ec2}:network-interface/*" },
    { Sid = "ManageOwnedResources", Effect = "Allow", Action = ["ec2:DeleteVpc", "ec2:ModifyVpcAttribute", "ec2:DeleteSubnet", "ec2:DeleteRouteTable", "ec2:CreateRoute", "ec2:ReplaceRoute", "ec2:DeleteRoute", "ec2:AssociateRouteTable", "ec2:DisassociateRouteTable", "ec2:AttachInternetGateway", "ec2:DetachInternetGateway", "ec2:DeleteInternetGateway", "ec2:DeleteSecurityGroup", "ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress", "ec2:ReleaseAddress", "ec2:AssociateAddress", "ec2:DisassociateAddress", "ec2:AttachVolume", "ec2:DetachVolume", "ec2:DeleteVolume", "ec2:ModifyVolume", "ec2:StartInstances", "ec2:StopInstances", "ec2:RebootInstances", "ec2:TerminateInstances", "ec2:ModifyInstanceAttribute", "ec2:ModifyInstanceCreditSpecification", "ec2:ModifyInstanceMetadataOptions", "ec2:CreateTags", "ec2:DeleteTags"], Resource = "${local.ec2}:*/*", Condition = { StringEquals = { "aws:ResourceTag/Project" = "dance-studio-agent", "aws:ResourceTag/Purpose" = "ec2-application" } } },
    { Sid = "TagOnCreation", Effect = "Allow", Action = "ec2:CreateTags", Resource = "${local.ec2}:*/*", Condition = { StringEquals = { "aws:RequestTag/Project" = "dance-studio-agent", "aws:RequestTag/Purpose" = "ec2-application", "ec2:CreateAction" = ["CreateVpc", "CreateSubnet", "CreateRouteTable", "CreateInternetGateway", "CreateSecurityGroup", "AllocateAddress", "CreateVolume", "RunInstances", "AuthorizeSecurityGroupIngress", "AuthorizeSecurityGroupEgress"] } } },
    { Sid = "ReadRuntimeRole", Effect = "Allow", Action = ["iam:GetRole", "iam:GetInstanceProfile"], Resource = ["arn:aws:iam::${local.account}:role/dance-studio-ec2-runtime", "arn:aws:iam::${local.account}:instance-profile/dance-studio-ec2-runtime"] },
    { Sid = "PassRuntimeRole", Effect = "Allow", Action = "iam:PassRole", Resource = "arn:aws:iam::${local.account}:role/dance-studio-ec2-runtime", Condition = { StringEquals = { "iam:PassedToService" = "ec2.amazonaws.com" } } },
    { Sid = "SendDeploymentCommands", Effect = "Allow", Action = "ssm:SendCommand", Resource = "arn:aws:ssm:ap-southeast-2::document/AWS-RunShellScript" },
    { Sid = "TargetOwnedServer", Effect = "Allow", Action = "ssm:SendCommand", Resource = "arn:aws:ec2:ap-southeast-2:${local.account}:instance/*", Condition = { StringEquals = { "ssm:resourceTag/Project" = "dance-studio-agent", "ssm:resourceTag/Purpose" = "ec2-application" } } },
    { Sid = "ApplicationSecret", Effect = "Allow", Action = ["secretsmanager:CreateSecret", "secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue", "secretsmanager:PutSecretValue", "secretsmanager:GetResourcePolicy", "secretsmanager:TagResource", "secretsmanager:UntagResource"], Resource = "arn:aws:secretsmanager:ap-southeast-2:${local.account}:secret:dance-studio-demo/application-*" },
    { Sid = "ApplicationBucket", Effect = "Allow", Action = ["s3:CreateBucket", "s3:ListBucket", "s3:GetBucket*", "s3:PutBucket*", "s3:GetEncryptionConfiguration", "s3:PutEncryptionConfiguration", "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration", "s3:GetBucketPublicAccessBlock", "s3:PutBucketPublicAccessBlock", "s3:GetBucketOwnershipControls", "s3:PutBucketOwnershipControls", "s3:GetAccelerateConfiguration", "s3:GetReplicationConfiguration", "s3:GetObjectLockConfiguration"], Resource = "arn:aws:s3:::${local.bucket}" },
    { Sid = "ReleaseArtifactsAndRestore", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = ["arn:aws:s3:::${local.bucket}/releases/*", "arn:aws:s3:::${local.bucket}/backups/*"] },
    { Sid = "StateBucket", Effect = "Allow", Action = ["s3:ListBucket", "s3:GetBucketLocation"], Resource = "arn:aws:s3:::${local.state}" },
    { Sid = "StateAndLock", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = ["arn:aws:s3:::${local.state}/ec2-demo/terraform.tfstate", "arn:aws:s3:::${local.state}/ec2-demo/terraform.tfstate.tflock"] },
    { Sid = "ReleaseStateLock", Effect = "Allow", Action = "s3:DeleteObject", Resource = "arn:aws:s3:::${local.state}/ec2-demo/terraform.tfstate.tflock" },
    { Sid = "ReadPricing", Effect = "Allow", Action = "pricing:GetProducts", Resource = "*" },
    { Sid = "ReadAlarms", Effect = "Allow", Action = "cloudwatch:DescribeAlarms", Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2" } } },
    { Sid = "ApplicationAlarms", Effect = "Allow", Action = ["cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms", "cloudwatch:ListTagsForResource", "cloudwatch:TagResource", "cloudwatch:UntagResource"], Resource = "arn:aws:cloudwatch:ap-southeast-2:${local.account}:alarm:dance-studio-demo-*" }
  ]
}
resource "aws_iam_policy" "deployment" {
  for_each = { infrastructure = slice(local.deployment_statements, 0, 12), operations = slice(local.deployment_statements, 12, length(local.deployment_statements)) }
  name     = "dance-studio-ec2-${each.key}"
  policy   = jsonencode({ Version = "2012-10-17", Statement = each.value })
  tags     = local.tags
}
resource "aws_iam_role_policy_attachment" "deployment" {
  for_each   = aws_iam_policy.deployment
  role       = data.aws_iam_role.deployer.name
  policy_arn = each.value.arn
}
output "backend" {
  value = {
    bucket       = aws_s3_bucket.state.id
    key          = "ec2-demo/terraform.tfstate"
    region       = "ap-southeast-2"
    use_lockfile = true
    encrypt      = true
    assume_role  = { role_arn = data.aws_iam_role.deployer.arn }
  }
}
output "deployment_policy" { value = { for key, policy in aws_iam_policy.deployment : key => jsondecode(policy.policy) } }
