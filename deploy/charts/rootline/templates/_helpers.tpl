{{/*
rootline.podSecurityContext (INF-022): pod-level security context shared by every Rootline pod.
*/}}
{{- define "rootline.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: 10001
runAsGroup: 10001
fsGroup: 10001
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{/*
rootline.containerSecurityContext (INF-022): container-level security context.
*/}}
{{- define "rootline.containerSecurityContext" -}}
readOnlyRootFilesystem: true
allowPrivilegeEscalation: false
capabilities:
  drop: [ALL]
{{- end -}}

{{/*
rootline.image: `<registry>/<component>:<tag>`. Argument: dict "Values" .Values "component" "<name>".
The registry is evaluated with `tpl` so values-gke.yaml can embed the GCP project.
*/}}
{{- define "rootline.image" -}}
{{ tpl .Values.image.registry (dict "Values" .Values) }}/{{ .component }}:{{ .Values.image.tag }}
{{- end -}}

{{/*
rootline.probes: liveness `/healthz` (period 10 s) and readiness `/readyz` (period 5 s) on the container port `http`.
*/}}
{{- define "rootline.probes" -}}
livenessProbe:
  httpGet: {path: /healthz, port: http}
  periodSeconds: 10
readinessProbe:
  httpGet: {path: /readyz, port: http}
  periodSeconds: 5
{{- end -}}

{{/*
rootline.otelEnv: OpenTelemetry environment variables. Argument: dict "component" "<name>".
*/}}
{{- define "rootline.otelEnv" -}}
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: http://otel-collector.observability.svc.cluster.local:4317
- name: OTEL_SERVICE_NAME
  value: rootline-{{ .component }}
{{- end -}}

{{/*
rootline.keycloakTokenVolume (SEC-033): projected ServiceAccount token, audience https://auth.D/realms/rootline,
expirationSeconds 600. Mount it with rootline.keycloakTokenVolumeMount.
*/}}
{{- define "rootline.keycloakTokenVolume" -}}
name: keycloak-token
projected:
  sources:
    - serviceAccountToken:
        audience: https://auth.{{ .Values.global.domain }}/realms/rootline
        expirationSeconds: 600
        path: keycloak-token
{{- end -}}

{{- define "rootline.keycloakTokenVolumeMount" -}}
name: keycloak-token
mountPath: /var/run/secrets/rootline/keycloak-token
readOnly: true
{{- end -}}
