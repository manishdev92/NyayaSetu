# Hosted zone must exist before apply (e.g. register nyayasetu.in in Route 53, or create a public hosted zone and delegate NS at your registrar).

data "aws_route53_zone" "web" {
  count = local.use_custom_web_domain ? 1 : 0

  name         = "${trimspace(var.web_custom_domain)}."
  private_zone = false
}
