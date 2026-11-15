terraform {
  required_version = ">= 1.10"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 6.0" }
    awscc  = { source = "hashicorp/awscc", version = "~> 1.0" }
    random = { source = "hashicorp/random", version = "~> 3.7" }
  }
}

variable "enable_data_api" { default = false }
variable "deployer_role_arn" { type = string }
variable "name" { type = string }
variable "lambda_zip" { type = string }
provider "aws" {
  region = "ap-southeast-2"
  assume_role { role_arn = var.deployer_role_arn }
  default_tags { tags = { Project = "dance-studio-agent", Purpose = "data-api-validation" } }
}
provider "awscc" {
  region      = "ap-southeast-2"
  assume_role = { role_arn = var.deployer_role_arn }
}
resource "awscc_rds_db_cluster" "test" {
  db_cluster_identifier               = var.name
  engine                              = "aurora-postgresql"
  with_express_configuration          = true
  enable_http_endpoint                = var.enable_data_api ? true : null
  deletion_protection                 = false
  serverless_v2_scaling_configuration = { min_capacity = 0, max_capacity = 2, seconds_until_auto_pause = 300 }
  tags                                = [{ key = "Project", value = "dance-studio-agent" }, { key = "Purpose", value = "data-api-validation" }]
}
resource "random_password" "database" {
  length  = 40
  special = false
}
resource "aws_secretsmanager_secret" "database" {
  name                    = "${var.name}-database"
  recovery_window_in_days = 0
}
resource "aws_secretsmanager_secret_version" "database" {
  secret_id     = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({ username = "validator", password = random_password.database.result })
}
locals { functions = toset(["api", "baseline"]) }
data "aws_iam_role" "function" {
  for_each = local.functions
  name     = "dance-studio-validation-${each.key}"
}
resource "aws_cloudwatch_log_group" "function" {
  for_each          = local.functions
  name              = "/aws/lambda/${var.name}-${each.key}"
  retention_in_days = 1
}
resource "aws_lambda_function" "test" {
  for_each         = local.functions
  function_name    = "${var.name}-${each.key}"
  role             = data.aws_iam_role.function[each.key].arn
  runtime          = "python3.12"
  handler          = "experiments.data_api.lambda_function.handler"
  architectures    = ["x86_64"]
  timeout          = 300
  memory_size      = 1024
  filename         = var.lambda_zip
  source_code_hash = fileexists(var.lambda_zip) ? filebase64sha256(var.lambda_zip) : null
  environment { variables = each.key == "api" ? {
    CLUSTER_ARN = awscc_rds_db_cluster.test.db_cluster_arn, SECRET_ARN = aws_secretsmanager_secret.database.arn
    } : {
    DB_HOST = awscc_rds_db_cluster.test.endpoint.address, DB_USER = "baseline", DB_AUTH = "iam"
  } }
  depends_on = [aws_cloudwatch_log_group.function, aws_secretsmanager_secret_version.database]
}
output "connection" {
  value = {
    ClusterArn = awscc_rds_db_cluster.test.db_cluster_arn
    ClusterId  = awscc_rds_db_cluster.test.db_cluster_identifier
    ResourceId = awscc_rds_db_cluster.test.db_cluster_resource_id
    Host       = awscc_rds_db_cluster.test.endpoint.address
    SecretArn  = aws_secretsmanager_secret.database.arn
    Api        = aws_lambda_function.test["api"].function_name
    Baseline   = aws_lambda_function.test["baseline"].function_name
  }
}

variable "python_executable" { type = string }
variable "backend_directory" { type = string }
resource "terraform_data" "no_snapshot_cleanup" {
  input = {
    name    = awscc_rds_db_cluster.test.db_cluster_identifier
    role    = var.deployer_role_arn
    python  = var.python_executable
    backend = var.backend_directory
  }
  provisioner "local-exec" {
    when        = destroy
    command     = "\"$VALIDATION_PYTHON\" -m experiments.data_api.delete_express --name \"$VALIDATION_CLUSTER\" --role \"$VALIDATION_ROLE\""
    working_dir = self.input.backend
    environment = {
      VALIDATION_PYTHON  = self.input.python
      VALIDATION_CLUSTER = self.input.name
      VALIDATION_ROLE    = self.input.role
    }
  }
}
