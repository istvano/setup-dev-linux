# Linux delivery source review

Observation date: 2026-09-13. Generated from
[source-review.json](../catalogue/source-review.json). This is a pre-build
evidence ledger, **not an executable installation lock or delivery approval**.

Coverage: **151 selected package/extension capabilities**,
**153 artifact candidates**, **17 inspected extension roots**.
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

See [pre-build review](PRE-BUILD-REVIEW.md) for decisions and principal blockers.

## Selected artifact candidates

| Capability | Proposed source | Observed version(s) | Integrity evidence |
|---|---|---|---|
| `actionlint` | upstream-release | v1.7.12 | published-only |
| `age` | ubuntu-apt | 1.2.1-1build1 | cached-apt-metadata |
| `ansible-core` | uv-lock | 2.21.4 | published-only |
| `ansible-lint` | uv-lock | 26.8.0 | published-only |
| `argocd` | upstream-release | v3.5.2 | published-only |
| `atuin` | ubuntu-apt | 18.8.0-1.3 | cached-apt-metadata |
| `aws-cli` | ubuntu-apt | 2.31.35-1 | cached-apt-metadata |
| `azure-cli` | vendor-apt | 2.90.0-1~resolute | published-only |
| `baobab` | ubuntu-apt | 49.1-2 | cached-apt-metadata |
| `bat` | ubuntu-apt | 0.25.0-5ubuntu1 | cached-apt-metadata |
| `bitwarden` | candidate-snap | 2026.8.0 | published-only |
| `btop` | ubuntu-apt | 1.4.6-2 | cached-apt-metadata |
| `chezmoi` | upstream-release | v2.72.1 | published-only |
| `claude-code` | upstream-release | 2.1.236 | published-only |
| `cline` | isolated-npm | 3.0.61 | published-only |
| `cloud-init` | ubuntu-apt | 26.1-0ubuntu3~26.04.1 | cached-apt-metadata |
| `codex` | upstream-release | rust-v0.154.0 | published-only |
| `containerd` | vendor-apt | 2.3.5-1~ubuntu.26.04~resolute | published-only |
| `controller-python` | uv-python | 20260901 | published-only |
| `curl` | ubuntu-apt | 8.18.0-1ubuntu2.5 | cached-apt-metadata |
| `dbeaver` | upstream-release | 26.2.0 | published-only |
| `dconf-editor` | ubuntu-apt | 49.0-1 | cached-apt-metadata |
| `deja-dup` | ubuntu-apt | 50.0-3 | cached-apt-metadata |
| `delta` | ubuntu-apt | 0.18.2-8 | cached-apt-metadata |
| `direnv` | ubuntu-apt | 2.37.1-1 | cached-apt-metadata |
| `dive` | upstream-release | v0.13.1 | published-only |
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
| `eza` | ubuntu-apt | 0.23.4-1ubuntu1 | cached-apt-metadata |
| `fd` | ubuntu-apt | 10.3.0-2ubuntu1 | cached-apt-metadata |
| `ffmpeg` | ubuntu-apt | 7:8.0.1-3ubuntu2 | cached-apt-metadata |
| `firefox` | candidate-snap | 155.0.1-1 | published-only |
| `flameshot` | ubuntu-apt | 13.3.0+git20251204-1 | cached-apt-metadata |
| `font-inconsolata` | ubuntu-apt | 001.010-6build2 | cached-apt-metadata |
| `font-jetbrains-mono-nerd` | upstream-release | v3.5.1 | published-only |
| `font-powerline` | ubuntu-apt | 2.8.4-1ubuntu0.1 | cached-apt-metadata |
| `fzf` | ubuntu-apt | 0.67.0-1 | cached-apt-metadata |
| `gedit` | ubuntu-apt | 48.1-9build1 | cached-apt-metadata |
| `gh` | ubuntu-apt | 2.46.0-4 | cached-apt-metadata |
| `ghostty` | ubuntu-apt | 1.3.0~us1-0ubuntu1.1 | cached-apt-metadata |
| `git` | ubuntu-apt | 1:2.53.0-1ubuntu1 | cached-apt-metadata |
| `git-lfs` | ubuntu-apt | 3.7.1-1 | cached-apt-metadata |
| `gitleaks` | ubuntu-apt | 8.16.0-1build2 | cached-apt-metadata |
| `gnome-disks` | ubuntu-apt | 46.1-2ubuntu2 | cached-apt-metadata |
| `gnome-extension-manager` | ubuntu-apt | 0.6.5-1 | cached-apt-metadata |
| `gnome-text-editor` | ubuntu-apt | 50.1-0ubuntu0.1 | cached-apt-metadata |
| `gnupg` | ubuntu-apt | 2.4.8-4ubuntu3.1 | cached-apt-metadata |
| `google-chrome` | vendor-apt | 153.0.8010.36-1 | published-only |
| `gparted` | ubuntu-apt | 1.8.0-1 | cached-apt-metadata |
| `gradle` | sdkman | 9.7.1 | published-only |
| `hadolint` | upstream-release | v2.15.1 | published-only |
| `helm` | upstream-release | v4.3.0 | published-only |
| `helmfile` | upstream-release | v1.7.4 | published-only |
| `htop` | ubuntu-apt | 3.4.1-5build2 | cached-apt-metadata |
| `httpie` | ubuntu-apt | 3.2.4-4 | cached-apt-metadata |
| `java` | sdkman | 21.0.12.1+1-LTS, 25.0.4.1+1-LTS | published-only |
| `jq` | ubuntu-apt | 1.8.1-4ubuntu2 | cached-apt-metadata |
| `just` | ubuntu-apt | 1.45.0-1 | cached-apt-metadata |
| `k3d` | upstream-release | v5.9.0 | published-only |
| `k9s` | upstream-release | v0.51.0 | published-only |
| `kind` | ubuntu-apt | 0.30.0-1 | cached-apt-metadata |
| `kotlin` | sdkman | v2.4.20 | published-only |
| `krew` | upstream-release | v0.5.0 | published-only |
| `krew-images` | krew | v0.6.5 | published-only |
| `krew-neat` | krew | v2.0.4 | published-only |
| `krew-sniff` | krew | v1.6.2 | published-only |
| `krew-tree` | krew | v0.6.0 | published-only |
| `krew-view-secret` | krew | v0.16.0 | published-only |
| `krew-whoami` | krew | v0.0.48 | published-only |
| `kubeconform` | upstream-release | v0.8.0 | published-only |
| `kubectl` | upstream-release | v1.37.0 | published-only |
| `kubectx` | ubuntu-apt | 0.9.5-2build1 | cached-apt-metadata |
| `kubeseal` | upstream-release | v0.40.0 | published-only |
| `kustomize` | ubuntu-apt | 5.8.0+ds-1 | cached-apt-metadata |
| `libreoffice` | ubuntu-apt | 4:26.2.5.2-0ubuntu0.26.04.1 | cached-apt-metadata |
| `libvirt` | ubuntu-apt | 12.0.0-1ubuntu5.3 | cached-apt-metadata |
| `mandrel` | sdkman | mandrel-25.0.0.1-Final | published-only |
| `maven` | sdkman | 3.9.11 | published-only |
| `mcedit` | provided-by | Unresolved / supplied by another capability | No artifact |
| `meld` | ubuntu-apt | 3.22.3-2 | cached-apt-metadata |
| `midnight-commander` | ubuntu-apt | 3:4.8.33-1.1build1 | cached-apt-metadata |
| `neovim` | ubuntu-apt | 0.11.6-1 | cached-apt-metadata |
| `net-tools` | ubuntu-apt | 2.10-2ubuntu1 | cached-apt-metadata |
| `networkmanager-openvpn` | ubuntu-apt | 1.12.5-1 | cached-apt-metadata |
| `node` | nvm | v22.23.2 | published-only |
| `nvidia-container-toolkit` | vendor-apt | 1.20.0-1 | published-only |
| `nvidia-driver` | ubuntu-apt | 580.178.04-0ubuntu0.26.04.1 | cached-apt-metadata |
| `nvm` | upstream-release | v0.40.7 | downloaded-observed |
| `nvtop` | ubuntu-apt | 3.2.0-2 | cached-apt-metadata |
| `obs-studio` | ubuntu-apt | 32.1.0-0ubuntu3 | cached-apt-metadata |
| `obsidian` | upstream-release | v1.13.7 | published-only |
| `oh-my-zsh` | upstream-release | be8da5c77192eb3da3699ea7c5e47bdfaa5eea4e | downloaded-observed |
| `opencode` | upstream-release | v1.18.30 | published-only |
| `opentofu` | upstream-release | v1.12.6 | published-only |
| `openvpn` | ubuntu-apt | 2.7.0-1ubuntu1.2 | cached-apt-metadata |
| `pnpm` | upstream-release | v12.4.1 | published-only |
| `pytest` | uv-lock | 9.1.1 | published-only |
| `python` | uv-python | 20260901 | published-only |
| `qemu` | ubuntu-apt | 1:10.2.1+ds-1ubuntu3.2 | cached-apt-metadata |
| `rclone` | ubuntu-apt | 1.60.1+dfsg-4ubuntu3.2 | cached-apt-metadata |
| `remmina` | ubuntu-apt | 1.4.43+dfsg-0ubuntu0.26.04.2 | cached-apt-metadata |
| `resources` | ubuntu-apt | 1.10.2-0ubuntu3.1 | cached-apt-metadata |
| `restic` | ubuntu-apt | 0.18.1-3ubuntu1 | cached-apt-metadata |
| `rhythmbox` | ubuntu-apt | 3.4.9-3ubuntu3 | cached-apt-metadata |
| `ripgrep` | ubuntu-apt | 15.1.0-1ubuntu1 | cached-apt-metadata |
| `scanner-utilities` | ubuntu-apt | 48.1-0ubuntu3, 1.4.0-1ubuntu1 | cached-apt-metadata |
| `sdkman` | upstream-release | 5.23.0 | published-only |
| `shellcheck` | ubuntu-apt | 0.11.0-2 | cached-apt-metadata |
| `shfmt` | ubuntu-apt | 3.12.0-1 | cached-apt-metadata |
| `shotwell` | ubuntu-apt | 0.32.13-2ubuntu1 | cached-apt-metadata |
| `showtime` | ubuntu-apt | 50.0-0ubuntu1 | cached-apt-metadata |
| `skopeo` | ubuntu-apt | 1.21.0~pre1-2build1 | cached-apt-metadata |
| `slack` | upstream-release | 4.52.155 | downloaded-observed |
| `sops` | upstream-release | v3.13.3 | published-only |
| `starship` | ubuntu-apt | 1.22.1-9ubuntu1 | cached-apt-metadata |
| `stern` | upstream-release | v1.34.0 | published-only |
| `terraform-docs` | upstream-release | v0.24.0 | published-only |
| `terragrunt` | upstream-release | v1.1.4 | published-only |
| `tmux` | ubuntu-apt | 3.6a-2ubuntu0.1 | cached-apt-metadata |
| `transmission` | ubuntu-apt | 4.1.1+dfsg-1ubuntu1.1 | cached-apt-metadata |
| `trivy` | upstream-release | v0.74.0 | published-only |
| `uv` | upstream-release | 0.12.13 | published-only |
| `vim` | ubuntu-apt | 2:9.1.2141-1ubuntu4.9 | cached-apt-metadata |
| `virt-manager` | ubuntu-apt | 1:5.1.0-1 | cached-apt-metadata |
| `vscode` | vendor-apt | 1.137.0-1788902055 | published-only |
| `wget` | ubuntu-apt | 1.25.0-2ubuntu4.4 | cached-apt-metadata |
| `yamllint` | ubuntu-apt | 1.37.1-1 | cached-apt-metadata |
| `yq` | upstream-release | v4.53.6 | published-only |
| `zed` | upstream-release | v1.19.2 | published-only |
| `zoxide` | ubuntu-apt | 0.9.8-1 | cached-apt-metadata |
| `zsh` | ubuntu-apt | 5.9-8ubuntu3 | cached-apt-metadata |
| `zsh-autosuggestions` | ubuntu-apt | 0.7.1-1build1 | cached-apt-metadata |
| `zsh-syntax-highlighting` | ubuntu-apt | 0.8.0-2build1 | cached-apt-metadata |

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
