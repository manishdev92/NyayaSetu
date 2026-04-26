# Second OIDC role for the GitHub "Destroy AWS (Terraform)" workflow: full account teardown via terraform destroy.
# The deploy role (github_deploy) cannot run destroy or manage Terraform state in S3. Trust is the same as deploy: this repo.
# attach AdministratorAccess — enough to delete the whole stack; tighten with a custom policy in production if required.
resource "aws_iam_role" "github_terraform_destroy" {
  name                 = "nyayasetu-github-terraform-destroy"
  assume_role_policy   = data.aws_iam_policy_document.github_assume.json
  max_session_duration = 3600
}

resource "aws_iam_role_policy_attachment" "github_terraform_destroy_admin" {
  role       = aws_iam_role.github_terraform_destroy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
