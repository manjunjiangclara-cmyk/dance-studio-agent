terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.0" }
  }
  backend "s3" {}
}
variable "account_id" { type = string }
variable "ami_id" { type = string }
variable "availability_zone" { type = string }
variable "instance_type" {
  type    = string
  default = "t3.small"
  validation {
    condition     = contains(["t3.small", "t3a.medium", "t3.medium"], var.instance_type)
    error_message = "Use a bounded x86 instance; the current Free Plan supports t3.small."
  }
}
variable "domain" {
  type    = string
  default = ""
  validation {
    condition     = var.domain == "" || can(regex("^[a-z0-9][a-z0-9.-]+[a-z0-9]$", var.domain))
    error_message = "Use a lowercase DNS hostname without a scheme, port, or path."
  }
}
variable "runtime_role_name" {
  type    = string
  default = "dance-studio-ec2-runtime"
}
provider "aws" {
  region = "ap-southeast-2"
  assume_role { role_arn = "arn:aws:iam::${var.account_id}:role/dance-studio-deployer" }
  default_tags { tags = { Project = "dance-studio-agent", Environment = "demo", Purpose = "ec2-application" } }
}
locals {
  name   = "dance-studio-demo"
  bucket = "${local.name}-${var.account_id}-ap-southeast-2"
  domain = var.domain != "" ? var.domain : "studio.${replace(aws_eip.web.public_ip, ".", "-")}.sslip.io"
}
resource "aws_vpc" "app" {
  cidr_block           = "10.83.0.0/24"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = local.name }
}
resource "aws_subnet" "app" {
  vpc_id            = aws_vpc.app.id
  cidr_block        = "10.83.0.0/26"
  availability_zone = var.availability_zone
  tags              = { Name = local.name }
}
resource "aws_internet_gateway" "app" {
  vpc_id = aws_vpc.app.id
  tags   = { Name = local.name }
}
resource "aws_route_table" "app" {
  vpc_id = aws_vpc.app.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.app.id
  }
  tags = { Name = local.name }
}
resource "aws_route_table_association" "app" {
  subnet_id      = aws_subnet.app.id
  route_table_id = aws_route_table.app.id
}
resource "aws_security_group" "web" {
  name        = local.name
  description = "HTTPS app and HTTP ACME challenge only; administration uses SSM"
  vpc_id      = aws_vpc.app.id
  tags        = { Name = local.name }
}
resource "aws_vpc_security_group_ingress_rule" "web" {
  for_each          = toset(["80", "443"])
  security_group_id = aws_security_group.web.id
  ip_protocol       = "tcp"
  from_port         = tonumber(each.key)
  to_port           = tonumber(each.key)
  cidr_ipv4         = "0.0.0.0/0"
  tags              = { Name = "${local.name}-${each.key}" }
}
resource "aws_vpc_security_group_egress_rule" "outbound" {
  security_group_id = aws_security_group.web.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
  tags              = { Name = "${local.name}-outbound" }
}
resource "aws_eip" "web" {
  domain = "vpc"
  tags   = { Name = local.name }
}
resource "aws_ebs_volume" "data" {
  availability_zone = var.availability_zone
  size              = 20
  type              = "gp3"
  encrypted         = true
  tags              = { Name = "${local.name}-data" }
  lifecycle { prevent_destroy = true }
}
resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.name}/application"
  recovery_window_in_days = 30
  lifecycle { prevent_destroy = true }
}
resource "aws_instance" "app" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.app.id
  vpc_security_group_ids      = [aws_security_group.web.id]
  associate_public_ip_address = false
  iam_instance_profile        = var.runtime_role_name
  monitoring                  = false
  disable_api_termination     = true
  credit_specification { cpu_credits = "standard" }
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }
  root_block_device {
    volume_size           = 40
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
    tags                  = { Project = "dance-studio-agent", Environment = "demo", Purpose = "ec2-application" }
  }
  user_data_base64 = base64gzip(templatefile("${path.module}/cloud-init.sh.tftpl", {
    volume_id   = aws_ebs_volume.data.id
    bucket      = local.bucket
    secret_arn  = aws_secretsmanager_secret.app.arn
    domain      = local.domain
    host_python = file("${path.module}/../../deployment/ec2/host.py")
    release     = file("${path.module}/../../deployment/ec2/release.sh")
    backup      = file("${path.module}/../../deployment/ec2/backup.sh")
  }))
  user_data_replace_on_change = false
  tags                        = { Name = local.name }
  depends_on                  = [aws_route_table_association.app]
  lifecycle {
    prevent_destroy = true
    # Cloud-init is initial host setup. Reviewed release archives update host helpers.
    ignore_changes = [user_data_base64]
  }
}
resource "aws_volume_attachment" "data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.app.id
}
resource "aws_eip_association" "web" {
  allocation_id = aws_eip.web.id
  instance_id   = aws_instance.app.id
}
resource "aws_s3_bucket" "operations" {
  bucket        = local.bucket
  force_destroy = false
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_public_access_block" "operations" {
  bucket                  = aws_s3_bucket.operations.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "operations" {
  bucket = aws_s3_bucket.operations.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "operations" {
  bucket = aws_s3_bucket.operations.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_policy" "operations" {
  bucket = aws_s3_bucket.operations.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.operations.arn, "${aws_s3_bucket.operations.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } }
  }] })
}
resource "aws_s3_bucket_lifecycle_configuration" "operations" {
  bucket = aws_s3_bucket.operations.id
  rule {
    id     = "backup-retention"
    status = "Enabled"
    filter { prefix = "backups/" }
    expiration { days = 30 }
    noncurrent_version_expiration { noncurrent_days = 7 }
  }
  rule {
    id     = "release-retention"
    status = "Enabled"
    filter { prefix = "releases/" }
    expiration { days = 90 }
    noncurrent_version_expiration { noncurrent_days = 7 }
  }
}
resource "aws_cloudwatch_metric_alarm" "status" {
  alarm_name          = "${local.name}-instance-status"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  dimensions          = { InstanceId = aws_instance.app.id }
  treat_missing_data  = "missing"
}
output "deployment" {
  value = {
    instance_id = aws_instance.app.id
    public_ip   = aws_eip.web.public_ip
    origin      = "https://${local.domain}"
    callback    = "https://${local.domain}/auth/callback"
    bucket      = aws_s3_bucket.operations.id
    secret_arn  = aws_secretsmanager_secret.app.arn
    data_volume = aws_ebs_volume.data.id
  }
}
