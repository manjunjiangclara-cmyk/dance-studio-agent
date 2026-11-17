terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
}
provider "aws" { region = "ap-southeast-2" }
data "aws_caller_identity" "current" {}
resource "aws_iam_role" "deployer" {
  name = "dance-studio-deployer"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/aiengineer" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = { Project = "dance-studio-agent", Purpose = "data-api-validation" }
}
resource "aws_iam_role_policy" "deployment" {
  name = "dance-studio-validation"
  role = aws_iam_role.deployer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["cloudformation:CreateResource", "cloudformation:GetResource", "cloudformation:UpdateResource", "cloudformation:DeleteResource", "cloudformation:GetResourceRequestStatus", "cloudformation:CancelResourceRequest"], Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2" } } },
      {
        Sid       = "NetworkRead"
        Effect    = "Allow"
        Action    = ["ec2:DescribeVpcs", "ec2:DescribeVpcAttribute", "ec2:DescribeSubnets", "ec2:DescribeAvailabilityZones", "ec2:DescribeSecurityGroups", "ec2:DescribeSecurityGroupRules", "ec2:DescribeTags", "ec2:DescribeNetworkInterfaces", "ec2:DescribeAccountAttributes"]
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2" } }
      },
      {
        Sid       = "CreateTaggedValidationNetwork"
        Effect    = "Allow"
        Action    = ["ec2:CreateVpc", "ec2:CreateSubnet", "ec2:CreateSecurityGroup"]
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2", "aws:RequestTag/Project" = "dance-studio-agent", "aws:RequestTag/Purpose" = "data-api-validation" } }
      },
      {
        Sid       = "CreateChildrenInValidationVpc"
        Effect    = "Allow"
        Action    = ["ec2:CreateSubnet", "ec2:CreateSecurityGroup"]
        Resource  = "arn:aws:ec2:ap-southeast-2:${data.aws_caller_identity.current.account_id}:vpc/*"
        Condition = { StringEquals = { "aws:ResourceTag/Project" = "dance-studio-agent", "aws:ResourceTag/Purpose" = "data-api-validation" } }
      },
      {
        Sid       = "ManageTaggedValidationNetwork"
        Effect    = "Allow"
        Action    = ["ec2:DeleteVpc", "ec2:ModifyVpcAttribute", "ec2:DeleteSubnet", "ec2:DeleteSecurityGroup", "ec2:AuthorizeSecurityGroupIngress", "ec2:RevokeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupEgress", "ec2:CreateTags", "ec2:DeleteTags"]
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2", "aws:ResourceTag/Project" = "dance-studio-agent", "aws:ResourceTag/Purpose" = "data-api-validation" } }
      },
      {
        Sid       = "TagOnNetworkCreation"
        Effect    = "Allow"
        Action    = "ec2:CreateTags"
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2", "aws:RequestTag/Project" = "dance-studio-agent", "aws:RequestTag/Purpose" = "data-api-validation", "ec2:CreateAction" = ["CreateVpc", "CreateSubnet", "CreateSecurityGroup"] } }
      },
      {
        Effect    = "Allow"
        Action    = ["rds:Describe*", "logs:DescribeLogGroups", "cloudwatch:GetMetricStatistics"]
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2" } }
      },
      {
        Effect   = "Allow"
        Action   = ["rds:EnableInternetAccessGateway", "rds:EnableHttpEndpoint", "rds:DisableHttpEndpoint", "rds:CreateDBCluster", "rds:DeleteDBCluster", "rds:ModifyDBCluster", "rds:CreateDBInstance", "rds:DeleteDBInstance", "rds:ModifyDBInstance", "rds:CreateDBSubnetGroup", "rds:DeleteDBSubnetGroup", "rds:AddTagsToResource", "rds:RemoveTagsFromResource", "rds:ListTagsForResource", "rds-data:ExecuteStatement", "rds-data:BeginTransaction", "rds-data:CommitTransaction", "rds-data:RollbackTransaction"]
        Resource = ["arn:aws:rds:ap-southeast-2:${data.aws_caller_identity.current.account_id}:*:data-api-validation-*", "arn:aws:rds:ap-southeast-2:${data.aws_caller_identity.current.account_id}:pg:default.aurora-postgresql17", "arn:aws:rds:ap-southeast-2:${data.aws_caller_identity.current.account_id}:cluster-pg:default.aurora-postgresql17"]
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:CreateFunction", "lambda:DeleteFunction", "lambda:Get*", "lambda:ListVersionsByFunction", "lambda:GetFunctionConfiguration", "lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration", "lambda:InvokeFunction", "lambda:TagResource", "lambda:UntagResource", "lambda:ListTags", "lambda:GetRuntimeManagementConfig", "lambda:GetPolicy"]
        Resource = "arn:aws:lambda:ap-southeast-2:${data.aws_caller_identity.current.account_id}:function:data-api-validation-*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:GetRole", "iam:PassRole"]
        Resource = [for role in aws_iam_role.runtime : role.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:CreateSecret", "secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue", "secretsmanager:DeleteSecret", "secretsmanager:PutSecretValue", "secretsmanager:TagResource", "secretsmanager:UntagResource", "secretsmanager:GetResourcePolicy"]
        Resource = "arn:aws:secretsmanager:ap-southeast-2:${data.aws_caller_identity.current.account_id}:secret:data-api-validation-*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy", "logs:TagResource", "logs:UntagResource", "logs:ListTagsForResource"]
        Resource = "arn:aws:logs:ap-southeast-2:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/data-api-validation-*"
      }
    ]
  })
}
output "role_arn" { value = aws_iam_role.deployer.arn }

resource "aws_iam_role" "runtime" {
  for_each           = toset(["api", "baseline"])
  name               = "dance-studio-validation-${each.key}"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = { Project = "dance-studio-agent", Purpose = "data-api-validation" }
}
resource "aws_iam_role_policy" "runtime" {
  for_each = aws_iam_role.runtime
  role     = each.value.id
  name     = "validation-runtime"
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Effect = "Deny", Action = ["ec2:CreateNetworkInterface", "ec2:DeleteNetworkInterface", "ec2:AssignPrivateIpAddresses", "ec2:UnassignPrivateIpAddresses"], Resource = "*", Condition = { ArnLike = { "lambda:SourceFunctionArn" = "arn:aws:lambda:ap-southeast-2:${data.aws_caller_identity.current.account_id}:function:data-api-validation-*" } } },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "arn:aws:logs:ap-southeast-2:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/data-api-validation-*:*" }
    ], jsondecode(each.key == "api" ? jsonencode([
      { Effect = "Allow", Action = ["rds-data:ExecuteStatement", "rds-data:BeginTransaction", "rds-data:CommitTransaction", "rds-data:RollbackTransaction"], Resource = "arn:aws:rds:ap-southeast-2:${data.aws_caller_identity.current.account_id}:cluster:data-api-validation-*" },
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = "arn:aws:secretsmanager:ap-southeast-2:${data.aws_caller_identity.current.account_id}:secret:data-api-validation-*" }
      ]) : jsonencode([
      { Effect = "Allow", Action = ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DescribeSubnets", "ec2:DeleteNetworkInterface", "ec2:AssignPrivateIpAddresses", "ec2:UnassignPrivateIpAddresses"], Resource = "*", Condition = { StringEquals = { "aws:RequestedRegion" = "ap-southeast-2" } } }
  ]))) })
}

variable "express_cluster_resource_id" {
  type    = string
  default = ""
  validation {
    condition     = var.express_cluster_resource_id == "" || can(regex("^cluster-[A-Za-z0-9]+$", var.express_cluster_resource_id))
    error_message = "Use the actual resource ID of this run's Express cluster."
  }
}
resource "aws_iam_role_policy" "express_admin" {
  count  = var.express_cluster_resource_id == "" ? 0 : 1
  role   = aws_iam_role.deployer.id
  name   = "express-fixture-bootstrap"
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "rds-db:connect", Resource = "arn:aws:rds-db:ap-southeast-2:${data.aws_caller_identity.current.account_id}:dbuser:${var.express_cluster_resource_id}/postgres" }] })
}
resource "aws_iam_role_policy" "express_baseline" {
  count  = var.express_cluster_resource_id == "" ? 0 : 1
  role   = aws_iam_role.runtime["baseline"].id
  name   = "express-baseline-connect"
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "rds-db:connect", Resource = "arn:aws:rds-db:ap-southeast-2:${data.aws_caller_identity.current.account_id}:dbuser:${var.express_cluster_resource_id}/baseline" }] })
}
