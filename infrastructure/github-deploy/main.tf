terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {}
}

provider "aws" { region = "ap-southeast-2" }
data "aws_caller_identity" "current" {}

variable "instance_id" {
  type = string
  validation {
    condition     = can(regex("^i-[0-9a-f]{17}$", var.instance_id))
    error_message = "Use the existing EC2 instance ID."
  }
}
variable "release_bucket" {
  type = string
  validation {
    condition     = can(regex("^dance-studio-demo-[0-9]{12}-ap-southeast-2$", var.release_bucket))
    error_message = "Use this account's dance studio release bucket."
  }
}

locals {
  account = data.aws_caller_identity.current.account_id
}

resource "aws_iam_role" "github_deploy" {
  name                 = "github-actions-dance-studio-deploy"
  max_session_duration = 7200
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = "arn:aws:iam::${local.account}:oidc-provider/token.actions.githubusercontent.com" }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = { StringEquals = {
        "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        "token.actions.githubusercontent.com:sub" = "repo:manjunjiangclara-cmyk@229754112/dance-studio-agent@1432691902:ref:refs/heads/master"
      } }
    }]
  })
}

resource "aws_ssm_document" "deploy" {
  name          = "DanceStudioDeploy"
  document_type = "Command"
  content = jsonencode({
    schemaVersion = "2.2"
    description   = "Deploy a checksum-verified dance studio release"
    parameters = {
      ReleaseSha = { type = "String", allowedPattern = "^[0-9a-f]{40}$" }
      Checksum   = { type = "String", allowedPattern = "^[0-9a-f]{64}$" }
    }
    mainSteps = [{
      action = "aws:runShellScript"
      name   = "DeployRelease"
      inputs = {
        timeoutSeconds = "3600"
        runCommand     = ["/usr/local/bin/studio-release {{ ReleaseSha }} {{ Checksum }}"]
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "release-only"
  role = aws_iam_role.github_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Sid = "ValidateTarget", Effect = "Allow", Action = "ec2:DescribeInstances", Resource = "*" },
      { Sid = "UploadRelease", Effect = "Allow", Action = ["s3:PutObject", "s3:AbortMultipartUpload"], Resource = "arn:aws:s3:::${var.release_bucket}/releases/*" },
      { Sid = "InvokeRelease", Effect = "Allow", Action = "ssm:SendCommand", Resource = [
        aws_ssm_document.deploy.arn,
        "arn:aws:ec2:ap-southeast-2:${local.account}:instance/${var.instance_id}"
      ] },
      { Sid = "ReadReleaseStatus", Effect = "Allow", Action = "ssm:GetCommandInvocation", Resource = "*" }
    ]
  })
}

output "role_arn" { value = aws_iam_role.github_deploy.arn }
