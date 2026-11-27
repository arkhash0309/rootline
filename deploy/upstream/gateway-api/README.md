# gateway-api

No Helm values: the `gateway-api-crds` Application (wave -4) syncs the standard-channel CRDs from
`https://github.com/kubernetes-sigs/gateway-api`, path `config/crd/standard`, at the git tag `v<gateway-api>` where
`<gateway-api>` is the `gateway-api` key of `versions.yaml` (`1.7.0` on 2026-11-27, tag `v1.7.0`).
