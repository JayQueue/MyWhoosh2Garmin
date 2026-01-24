```bash
terraform plan \
    -var="github_owner=${GITHUB_OWNER:-MarcChen}" \
    -var="github_repository=${GITHUB_REPOSITORY:-MyWhoosh2Garmin}" \
    -var="strava_client_id=${STRAVA_CLIENT_ID}" \
    -var="strava_client_secret=${STRAVA_CLIENT_SECRET}" \
    -var="strava_access_token=${STRAVA_ACCESS_TOKEN}" \
    -var="strava_refresh_token=${STRAVA_REFRESH_TOKEN}" \
    -var="strava_expires_at=${STRAVA_EXPIRES_AT}" \
    -var="strava_expires_in=${STRAVA_EXPIRES_IN}" \
    -var="garmin_tokens=${GARMIN_TOKENS}"
```