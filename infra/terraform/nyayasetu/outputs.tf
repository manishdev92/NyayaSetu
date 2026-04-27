output "ingest_corpus_bucket" {
  value = (
    length(aws_s3_bucket.ingest_corpus) > 0
    ? aws_s3_bucket.ingest_corpus[0].id
    : null
  )
  description = "S3 bucket for statute `.md` drops (empty = not created). Use s3://<id>/prefix/ with ingest_statutes --s3-uri."
}

output "aws_region" {
  value = var.aws_region
}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "ecr_api_repository_url" {
  value = module.ecr.api_repository_url
}

output "ecr_web_repository_url" {
  value = module.ecr.web_repository_url
}

output "github_deploy_role_arn" {
  value = aws_iam_role.github_deploy.arn
}

output "github_terraform_destroy_role_arn" {
  description = "IAM role for the GitHub Actions 'Destroy AWS (Terraform)' workflow (set repository secret AWS_TERRAFORM_DESTROY_ROLE_ARN)."
  value       = aws_iam_role.github_terraform_destroy.arn
}

output "apprunner_ecr_access_role_arn" {
  value = aws_iam_role.apprunner_ecr_access.arn
}

output "api_service_url" {
  description = "Public hostname (no scheme) for the API App Runner service."
  value       = length(aws_apprunner_service.api) > 0 ? aws_apprunner_service.api[0].service_url : null
}

output "api_public_url" {
  description = "HTTPS URL for the API."
  value       = length(aws_apprunner_service.api) > 0 ? "https://${aws_apprunner_service.api[0].service_url}" : null
}

output "web_service_url" {
  value = length(aws_apprunner_service.web) > 0 ? aws_apprunner_service.web[0].service_url : null
}

output "web_public_url" {
  value = length(aws_apprunner_service.web) > 0 ? "https://${aws_apprunner_service.web[0].service_url}" : null
}

output "api_service_arn" {
  value = length(aws_apprunner_service.api) > 0 ? aws_apprunner_service.api[0].arn : null
}

output "web_service_arn" {
  value = length(aws_apprunner_service.web) > 0 ? aws_apprunner_service.web[0].arn : null
}

output "web_cloudfront_domain" {
  description = "CloudFront default domain (dxxxx.cloudfront.net) for the web app; use for DNS CNAME/alias when adding freelytics-solutions.com."
  value       = length(aws_cloudfront_distribution.web) > 0 ? aws_cloudfront_distribution.web[0].domain_name : null
}

output "web_cloudfront_url" {
  description = "HTTPS URL to open the site via CloudFront (before a custom domain)."
  value       = length(aws_cloudfront_distribution.web) > 0 ? "https://${aws_cloudfront_distribution.web[0].domain_name}" : null
}

output "effective_web_app_public_url" {
  description = "URL used for NEXT_PUBLIC_APP_URL / CORS — custom domain (https://nyayasetu.in) when web_custom_domain is set, else web_app_public_url."
  value       = local.effective_web_app_public_url != "" ? local.effective_web_app_public_url : null
}

output "web_custom_domain" {
  description = "Apex hostname when custom domain is enabled (empty otherwise)."
  value       = local.use_custom_web_domain ? trimspace(var.web_custom_domain) : null
}
