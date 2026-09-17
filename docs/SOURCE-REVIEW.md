# Linux delivery source review

Observation date: 2026-09-13. Generated from
[source-review.json](../catalogue/source-review.json). This is a pre-build
evidence ledger, **not an executable installation lock or delivery approval**.

Coverage: **54 selected package/extension capabilities**,
**56 artifact candidates**, **17 inspected extension roots**.
Behavior/manual capabilities do not need artifact rows. Optional, pending and omitted
capabilities remain outside the selected delivery review.

## How to interpret the evidence

- `published-only`: a primary publisher/index supplies a digest; artifact bytes have not been checked.
- `cached-apt-metadata`: a trusted Ubuntu origin was observed in the local APT cache; this is not an end-to-end signature/package check.
- `downloaded-observed`: downloaded bytes were hashed; no independent published digest was compared.
- `downloaded-matched-published`: downloaded bytes matched the publisher digest.
- `missing-digest`: the candidate cannot become an integrity lock yet.

Metadata evidence includes its source URL and the SHA-256 of the observed response.
Licence labels are observations from publisher/source or installed-package metadata.
A HEAD licence file does not prove the terms of a different tagged binary or bundled
components. All records retain review-required status and explicit remaining work.
The catalogue therefore continues to report delivery as unverified.

APT candidates use the observed resolute, resolute-updates or resolute-security suites.
Package versions are observations, not permanent security-update freezes. Proposed
upstream sources for packages missing from APT need a deliberate source/policy change
before installation. Ghostty was found in Ubuntu package metadata; do not use a
community installer merely because the old candidate assumed an upstream download.

Simple Scan and SANE utilities were identified from installed package metadata.
This resolves the scanner group names, not physical-device/backend readiness.

Extension ZIP package manifests were inspected without executing them. Root IDs and
versions must agree with Marketplace metadata. Dependency/pack children are recorded
separately and still require review; they must not be silently accepted as root coverage.

Reasoning and outstanding gates are in [source evidence](SOURCE-EVIDENCE.md).

## Selected artifact candidates

| Capability | Proposed source | Observed version(s) | Integrity evidence |
|---|---|---|---|
| `ansible-core` | uv-lock | 2.21.4 | published-only |
| `ansible-lint` | uv-lock | 26.8.0 | published-only |
| `bitwarden` | candidate-snap | 2026.8.0 | published-only |
| `chezmoi` | upstream-release | v2.72.1 | published-only |
| `claude-code` | upstream-release | 2.1.236 | published-only |
| `cline` | isolated-npm | 3.0.61 | published-only |
| `codex` | upstream-release | rust-v0.154.0 | published-only |
| `containerd` | vendor-apt | 2.3.5-1~ubuntu.26.04~resolute | published-only |
| `controller-python` | uv-python | 20260901 | published-only |
| `docker-buildx` | vendor-apt | 0.37.1-1~ubuntu.26.04~resolute | published-only |
| `docker-compose` | vendor-apt | 5.5.1-1~ubuntu.26.04~resolute | published-only |
| `docker-engine` | vendor-apt | 5:29.8.0-1~ubuntu.26.04~resolute | published-only |
| `extension-anthropic.claude-code` | vscode-marketplace | 2.1.269 | downloaded-matched-published |
| `extension-dbaeumer.vscode-eslint` | vscode-marketplace | 3.0.34 | downloaded-matched-published |
| `extension-eamodio.gitlens` | vscode-marketplace | 19.1.0 | downloaded-matched-published |
| `extension-esbenp.prettier-vscode` | vscode-marketplace | 12.4.0 | downloaded-matched-published |
| `extension-golang.go` | vscode-marketplace | 0.56.1 | downloaded-matched-published |
| `extension-ms-azuretools.vscode-docker` | vscode-marketplace | 2.0.0 | downloaded-matched-published |
| `extension-ms-kubernetes-tools.vscode-kubernetes-tools` | vscode-marketplace | 1.4.1 | downloaded-matched-published |
| `extension-ms-python.python` | vscode-marketplace | 2026.4.0 | downloaded-matched-published |
| `extension-ms-toolsai.jupyter` | vscode-marketplace | 2025.9.1 | downloaded-matched-published |
| `extension-ms-vscode-remote.remote-containers` | vscode-marketplace | 0.469.0 | downloaded-matched-published |
| `extension-ms-vscode-remote.remote-ssh` | vscode-marketplace | 0.128.0 | downloaded-matched-published |
| `extension-ms-vscode.makefile-tools` | vscode-marketplace | 0.12.17 | downloaded-matched-published |
| `extension-openai.chatgpt` | vscode-marketplace | 26.908.40401 | downloaded-matched-published |
| `extension-redhat.vscode-xml` | vscode-marketplace | 0.29.3 | downloaded-matched-published |
| `extension-redhat.vscode-yaml` | vscode-marketplace | 1.24.0 | downloaded-matched-published |
| `extension-saoudrizwan.claude-dev` | vscode-marketplace | 4.1.17 | downloaded-matched-published |
| `extension-vscode-icons-team.vscode-icons` | vscode-marketplace | 12.19.0 | downloaded-matched-published |
| `firefox` | candidate-snap | 155.0.1-1 | published-only |
| `ghostty` | ubuntu-apt | 1.3.0~us1-0ubuntu1.1 | cached-apt-metadata |
| `gradle` | sdkman | 9.7.1 | published-only |
| `java` | sdkman | 21.0.12.1+1-LTS, 25.0.4.1+1-LTS | published-only |
| `kotlin` | sdkman | v2.4.20 | published-only |
| `krew-images` | krew | v0.6.5 | published-only |
| `krew-neat` | krew | v2.0.4 | published-only |
| `krew-sniff` | krew | v1.6.2 | published-only |
| `krew-tree` | krew | v0.6.0 | published-only |
| `krew-view-secret` | krew | v0.16.0 | published-only |
| `krew-whoami` | krew | v0.0.48 | published-only |
| `mandrel` | sdkman | mandrel-25.0.0.1-Final | published-only |
| `maven` | sdkman | 3.9.11 | published-only |
| `node` | nvm | v22.23.2 | published-only |
| `nvidia-container-toolkit` | vendor-apt | 1.20.0-1 | published-only |
| `nvm` | upstream-release | v0.40.7 | downloaded-observed |
| `oh-my-zsh` | upstream-release | be8da5c77192eb3da3699ea7c5e47bdfaa5eea4e | downloaded-observed |
| `opencode` | upstream-release | v1.18.30 | published-only |
| `pnpm` | upstream-release | v12.4.1 | published-only |
| `pytest` | uv-lock | 9.1.1 | published-only |
| `python` | uv-python | 20260901 | published-only |
| `sdkman` | upstream-release | 5.23.0 | published-only |
| `uv` | upstream-release | 0.12.13 | published-only |
| `yq` | upstream-release | v4.53.6 | published-only |
| `zed` | upstream-release | v1.19.2 | published-only |

## Extension dependency review

| Root | Required dependencies | Pack children |
|---|---|---|
| `anthropic.claude-code` | None declared | None declared |
| `dbaeumer.vscode-eslint` | None declared | None declared |
| `eamodio.gitlens` | None declared | None declared |
| `esbenp.prettier-vscode` | None declared | None declared |
| `golang.go` | None declared | None declared |
| `ms-azuretools.vscode-docker` | ms-azuretools.vscode-containers | None declared |
| `ms-kubernetes-tools.vscode-kubernetes-tools` | redhat.vscode-yaml | None declared |
| `ms-python.python` | None declared | ms-python.vscode-pylance, ms-python.debugpy, ms-python.vscode-python-envs |
| `ms-toolsai.jupyter` | None declared | ms-toolsai.jupyter-keymap, ms-toolsai.jupyter-renderers, ms-toolsai.vscode-jupyter-slideshow, ms-toolsai.vscode-jupyter-cell-tags |
| `ms-vscode-remote.remote-containers` | None declared | None declared |
| `ms-vscode-remote.remote-ssh` | None declared | ms-vscode-remote.remote-ssh-edit, ms-vscode.remote-explorer |
| `ms-vscode.makefile-tools` | None declared | None declared |
| `openai.chatgpt` | None declared | None declared |
| `redhat.vscode-xml` | None declared | None declared |
| `redhat.vscode-yaml` | None declared | None declared |
| `saoudrizwan.claude-dev` | None declared | None declared |
| `vscode-icons-team.vscode-icons` | None declared | None declared |
