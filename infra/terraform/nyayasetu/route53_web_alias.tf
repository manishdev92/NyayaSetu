# Point apex + www at CloudFront (same distribution; aliases on distribution must include both).

resource "aws_route53_record" "web_apex" {
  count = local.use_custom_web_domain && length(aws_cloudfront_distribution.web) > 0 ? 1 : 0

  zone_id = data.aws_route53_zone.web[0].zone_id
  name    = trimspace(var.web_custom_domain)
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.web[0].domain_name
    zone_id                = aws_cloudfront_distribution.web[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "web_www" {
  count = local.use_custom_web_domain && length(aws_cloudfront_distribution.web) > 0 ? 1 : 0

  zone_id = data.aws_route53_zone.web[0].zone_id
  name    = "www.${trimspace(var.web_custom_domain)}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.web[0].domain_name
    zone_id                = aws_cloudfront_distribution.web[0].hosted_zone_id
    evaluate_target_health = false
  }
}
