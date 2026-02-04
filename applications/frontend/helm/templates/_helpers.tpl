{{/* Chart name */}}
{{- define "frontend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Full name - always prefixed with leninkart- */}}
{{- define "frontend.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "leninkart-%s" (include "frontend.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/* Standard labels */}}
{{- define "frontend.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "frontend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app: frontend
{{- end }}

{{/* Selector labels - MUST match deployment pod labels */}}
{{- define "frontend.selectorLabels" -}}
app: frontend
{{- end }}
