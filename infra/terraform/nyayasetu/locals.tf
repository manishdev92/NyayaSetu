locals {
  # Custom domain (e.g. nyayasetu.in): ACM + Route 53 + CloudFront aliases — see docs/CUSTOM_DOMAIN_IN.md
  use_custom_web_domain = trimspace(var.web_custom_domain) != "" && var.deploy_web_service && var.create_cloudfront_web

  # Prefer https://<custom-domain> for CORS and NEXT_PUBLIC_APP_URL once set in tfvars.
  effective_web_app_public_url = (
    local.use_custom_web_domain
    ? "https://${trimspace(var.web_custom_domain)}"
    : trimspace(var.web_app_public_url)
  )
}
