# GCP Infrastructure

## Cloud Run Services

### Frontend
```bash
gcloud run deploy surensaas-front \
  --source ./surenSaasFront \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "BUILD_ID=$(git rev-parse --short HEAD)"
```

**Config**:
- CPU: 1
- Memory: 512Mi
- Concurrency: 80
- Max instances: 10
- Always-on (min instances: 1)

### Backend
```bash
gcloud run deploy surensaas-back \
  --source ./surenSaasBack \
  --platform managed \
  --region europe-west1 \
  --no-allow-unauthenticated \
  --set-env-vars "SUPABASE_URL=secret:supabase-url"
```

**Config**:
- CPU: 1
- Memory: 1Gi
- Concurrency: 100
- Max instances: 50
- Scale-to-zero (min instances: 0)

## Secret Manager
```bash
# Create secrets
gcloud secrets create supabase-url --data-file=-
gcloud secrets create supabase-service-key --data-file=-
gcloud secrets create microsoft-client-id --data-file=-
gcloud secrets create microsoft-client-secret --data-file=-

# Grant access to Cloud Run services
gcloud secrets add-iam-policy-binding supabase-url \
  --member="serviceAccount:xxx@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Networking
- **No custom domain**: gcp.run URLs
- **Strict CORS**: Whitelisted origins in an env variable
- **No VPC**: Communication via public HTTPS

## Automatic deployment
```bash
# Via Cloud Build (optional)
gcloud builds submit --config cloudbuild.yaml
```

## Costs
- Front: ~€5/month (always-on)
- Back: ~€0-10/month (scale-to-zero)
- Secrets: ~€0.10/month per secret
