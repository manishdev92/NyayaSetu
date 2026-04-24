variable "api_repository_name" {
  type    = string
  default = "nyayasetu-api"
}

variable "web_repository_name" {
  type    = string
  default = "nyayasetu-web"
}

variable "lifecycle_keep_count" {
  type    = number
  default = 15
}
