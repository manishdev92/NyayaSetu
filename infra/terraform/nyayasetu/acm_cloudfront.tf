# ACM certificate in us-east-1 (required for CloudFront custom domains).
# DNS validation via Route 53 records in the same account as the hosted zone.

resource "aws_acm_certificate" "web_cloudfront" {
  count = local.use_custom_web_domain ? 1 : 0

  provider = aws.us_east_1

  domain_name               = trimspace(var.web_custom_domain)
  subject_alternative_names = ["www.${trimspace(var.web_custom_domain)}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "web_cert_validation" {
  for_each = local.use_custom_web_domain ? {
    for dvo in aws_acm_certificate.web_cloudfront[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.web[0].zone_id
}

resource "aws_acm_certificate_validation" "web_cloudfront" {
  count = local.use_custom_web_domain ? 1 : 0

  provider = aws.us_east_1

  certificate_arn = aws_acm_certificate.web_cloudfront[0].arn
  validation_record_fqdns = [
    for r in aws_route53_record.web_cert_validation : r.fqdn
  ]

  depends_on = [aws_route53_record.web_cert_validation]
}
