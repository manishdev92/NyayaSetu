# Custom domain on `.in` (e.g. `nyayasetu.in`) — end to end

This stack serves the web app via **CloudFront** → **App Runner**. To use **`https://nyayasetu.in`** and **`https://www.nyayasetu.in`**, Terraform can request an **ACM certificate (us-east-1)**, complete **DNS validation** in **Route 53**, attach the cert to **CloudFront**, and create **alias A records**.

## What you need before `terraform apply`

1. **Own the name**  
   Register **`nyayasetu.in`** (or your chosen `.in` name) in **Route 53 → Registered domains**, **or** at another registrar.

2. **Hosted zone in this AWS account**  
   There must be a **public** Route 53 **hosted zone** whose name is exactly **`nyayasetu.in.`**  
   - If you registered in Route 53, the zone is usually created for you.  
   - If you registered elsewhere, **create a public hosted zone** for `nyayasetu.in` in Route 53 and set your registrar’s **name servers** to the four **NS** records shown for that zone (propagation can take up to 48 hours, often much less).

3. **Terraform variable**  
   In `terraform.tfvars.json` (or `-var` / environment):

   ```json
   "web_custom_domain": "nyayasetu.in"
   ```

   Leave **`web_app_public_url`** as your current CloudFront URL until the first successful apply with the custom domain; after that, **`effective_web_app_public_url`** becomes **`https://nyayasetu.in`** via `locals.tf` (apex takes precedence when `web_custom_domain` is set).

4. **Apply from a machine that can run Terraform** with your **S3 backend** (`backend.s3.hcl`) configured:

   ```bash
   cd infra/terraform/nyayasetu
   ./../../../scripts/nyayasetu-terraform-init.sh
   terraform plan
   terraform apply
   ```

   Order of creation: ACM (us-east-1) → Route 53 **validation** records → certificate **ISSUED** → CloudFront **aliases** + TLS → Route 53 **apex + www** alias → CloudFront.

## After Terraform succeeds

1. **`terraform output effective_web_app_public_url`**  
   Expect **`https://nyayasetu.in`**.

2. **GitHub Actions (frontend build)**  
   Set repository variable **`WEB_APP_PUBLIC_URL`** to **`https://nyayasetu.in`** so `NEXT_PUBLIC_APP_URL` is baked correctly on the next **Deploy AWS** run (see `.github/workflows/deploy-aws.yml`).

3. **Repository secret / API**  
   No change to **`NEXT_PUBLIC_API_URL`** unless your API hostname changed.

4. **Clerk**  
   In the Clerk dashboard, add **allowed origins / redirect URLs** for:
   - `https://nyayasetu.in`
   - `https://www.nyayasetu.in`  
   Remove or keep old CloudFront URLs during migration.

5. **Redeploy web**  
   Run **Deploy AWS** (or push to `main` under deploy paths) so App Runner / image env matches, or rely on Terraform-updated App Runner env on next apply.

6. **Smoke test**  
   Open **`https://nyayasetu.in/chat`**, sign-in, and confirm API calls succeed (CORS uses `effective_web_app_public_url`).

## Turning custom domain off

Set **`web_custom_domain`** to **`""`** and set **`web_app_public_url`** back to your **`https://dxxxx.cloudfront.net`** URL, then `terraform apply`. Review CloudFront + ACM replacement behaviour in a lower environment first.

## Files involved (Terraform)

| File | Role |
|------|------|
| `locals.tf` | `use_custom_web_domain`, `effective_web_app_public_url` |
| `versions.tf` | Provider **`aws.us_east_1`** for ACM |
| `acm_cloudfront.tf` | ACM cert + DNS validation + validation wait |
| `route53_zone.tf` | `data.aws_route53_zone` for `nyayasetu.in` |
| `route53_web_alias.tf` | Apex + **www** **A** alias → CloudFront |
| `cloudfront_web.tf` | **`aliases`**, **`viewer_certificate`** (ACM) |
| `apprunner.tf` | CORS + **`NEXT_PUBLIC_APP_URL`** from **`effective_web_app_public_url`** |

## Troubleshooting

- **`data.aws_route53_zone` not found** — Hosted zone name must be **`nyayasetu.in.`** (public), same account/region usage as intended.  
- **Certificate stuck on “Pending validation”** — NS at registrar must point to Route 53; validation CNAMEs must resolve.  
- **CloudFront 525 / TLS errors** — Wait for certificate **ISSUED** and distribution **Deployed**.  
- **Wrong site URL in the browser** — Update **`WEB_APP_PUBLIC_URL`**, Clerk, and redeploy the web image if needed.
