{{/*
rootline.root.appEnabled: renders "true" when the Application is enabled and, if `envs` is set, lists the
current environment. Argument: dict "app" <app values> "env" <.Values.env>.
*/}}
{{- define "rootline.root.appEnabled" -}}
{{- if and .app.enabled (or (not .app.envs) (has .env .app.envs)) -}}true{{- end -}}
{{- end -}}

{{/*
rootline.root.globalParameters: Helm parameters passed to every local chart (INF-020). Argument: root context.
*/}}
{{- define "rootline.root.globalParameters" -}}
- {name: global.env, value: {{ .Values.env | quote }}}
- {name: global.domain, value: {{ .Values.domain | quote }}}
- {name: global.gcpProject, value: {{ .Values.gcpProject | quote }}}
- {name: global.k8sIssuer, value: {{ .Values.k8sIssuer | quote }}}
- {name: global.artifactsBucket, value: {{ .Values.artifactsBucket | quote }}}
- {name: global.ingressIP, value: {{ .Values.ingressIP | quote }}}
{{- end -}}
