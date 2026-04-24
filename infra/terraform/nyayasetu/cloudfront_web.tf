# CloudFront in front of the web App Runner service (default *.cloudfront.net).
# Custom domain: add ACM in us-east-1 + alias on this distribution later.
# Origin request: AllViewerExceptHostHeader so Host sent to App Runner is the service hostname, not the viewer's.

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_distribution" "web" {
  count   = var.deploy_web_service && var.create_cloudfront_web ? 1 : 0
  comment = "NyayaSetu web (App Runner origin ap-south-1)"
  enabled = true

  is_ipv6_enabled     = true
  price_class         = "PriceClass_200"
  wait_for_deployment = true

  origin {
    domain_name = aws_apprunner_service.web[0].service_url
    origin_id   = "apprunner-nyayasetu-web"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "https-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 30
      origin_keepalive_timeout = 5
    }
  }

  default_cache_behavior {
    target_origin_id = "apprunner-nyayasetu-web"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    compress         = true

    # Next.js: no edge caching by default (SSR, auth); tune path-based behaviors later.
    cache_policy_id          = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
    smooth_streaming         = false
    viewer_protocol_policy   = "redirect-to-https"
  }

  restrictions {
    geo_restriction {
      locations        = []
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  depends_on = [aws_apprunner_service.web]
}
