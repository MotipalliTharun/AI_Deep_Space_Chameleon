# Infra (Terraform)

Dev-environment skeleton for AWS. See `main.tf` for the module TODOs staged
against the sprint plan in `docs/PRD.md` §9.

```bash
terraform init
terraform plan -var="environment=dev"
```

Do not `apply` until a remote state backend is configured (see the TODO in
`versions.tf`) and secrets are out of any `.tfvars` committed to git.
