output "api_repository_url" {
  value = module.ecr.api_repository_url
}

output "web_repository_url" {
  value = module.ecr.web_repository_url
}

output "registry_id" {
  value = module.ecr.registry_id
}

output "aws_region" {
  value = var.aws_region
}
