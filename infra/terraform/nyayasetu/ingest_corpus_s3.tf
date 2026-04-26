# Optional: private bucket for `*.md` statute drops (see backend `ingest_statutes --s3-uri` and
# `.github/workflows/pinecone-statute-s3-ingest.yml`). Set `ingest_corpus_bucket_name` to a
# **globally unique** name, or leave empty to skip.
resource "aws_s3_bucket" "ingest_corpus" {
  count  = trimspace(var.ingest_corpus_bucket_name) != "" ? 1 : 0
  bucket = trimspace(var.ingest_corpus_bucket_name)
}

resource "aws_s3_bucket_public_access_block" "ingest_corpus" {
  count  = length(aws_s3_bucket.ingest_corpus) > 0 ? 1 : 0
  bucket = aws_s3_bucket.ingest_corpus[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "ingest_corpus" {
  count  = length(aws_s3_bucket.ingest_corpus) > 0 ? 1 : 0
  bucket = aws_s3_bucket.ingest_corpus[0].id
  versioning_configuration {
    status = "Enabled"
  }
}
