# Moved and dropped items

Where each command-line item this repository used to install went. Written before
anything was removed, so no tool disappears silently; `tests/test_moved.py` fails when
an item leaves `manifest/*.json` without a row here. Items the host keeps (desktop
applications, drivers, GNOME, snaps, VS Code and its extensions, zed, obsidian, the
firewall) have no row.

Destinations are verified against `setup-dev-linux-wsl` main: a profile fragment
(`profiles/<name>.Brewfile`), its apt lists, its mise config or its chezmoi sources.
`dropped:<name>` points at a row of that repository's `docs/DROPPED.md`.

| Item | Destination | Note |
|---|---|---|
| `agent:claude` | `setup-dev-linux-wsl:ai-agents (apt/vendor.list)` | Claude Code from the signed Anthropic apt repository |
| `agent:cline` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` | mise npm backend |
| `agent:codex` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` | mise aqua backend |
| `agent:copilot` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` | mise npm backend |
| `agent:opencode` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` |  |
| `binary:actionlint` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` |  |
| `binary:argocd` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:chezmoi` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `binary:cilium` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` | Homebrew formula cilium-cli |
| `binary:d2` | `setup-dev-linux-wsl:docs (profiles/docs.Brewfile)` |  |
| `binary:dive` | `setup-dev-linux-wsl:security-scan (profiles/security-scan.Brewfile)` |  |
| `binary:grype` | `setup-dev-linux-wsl:security-scan (profiles/security-scan.Brewfile)` |  |
| `binary:hadolint` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` |  |
| `binary:helm` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:helmfile` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:hubble` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:k3d` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:k9s` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:krew` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:kubeconform` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:kubelogin` | `setup-dev-linux-wsl:cloud-azure (profiles/cloud-azure.Brewfile)` |  |
| `binary:kubeseal` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:osv-scanner` | `setup-dev-linux-wsl:security-scan (profiles/security-scan.Brewfile)` |  |
| `binary:sops` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `binary:stern` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `binary:syft` | `setup-dev-linux-wsl:security-scan (profiles/security-scan.Brewfile)` |  |
| `binary:terraform-docs` | `setup-dev-linux-wsl:cloud (profiles/cloud.Brewfile)` |  |
| `binary:terragrunt` | `setup-dev-linux-wsl:cloud (profiles/cloud.Brewfile)` |  |
| `binary:trufflehog` | `setup-dev-linux-wsl:security-scan (profiles/security-scan.Brewfile)` |  |
| `binary:yq` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `dotfile:.config/atuin/config.toml` | `setup-dev-linux-wsl:core (chezmoi/dot_config/atuin/config.toml)` |  |
| `dotfile:.config/starship.toml` | `setup-dev-linux-wsl:core (chezmoi/dot_config/starship.toml)` |  |
| `dotfile:.gitconfig` | `setup-dev-linux-wsl:core (chezmoi/dot_gitconfig.tmpl)` |  |
| `dotfile:.selected_editor` | `setup-dev-linux-wsl:core (chezmoi/dot_zshrc.tmpl)` | EDITOR=nvim in the zshrc |
| `dotfile:.zshrc` | `setup-dev-linux-wsl:core (chezmoi/dot_zshrc.tmpl)` |  |
| `krew:images` | `setup-dev-linux-wsl:kubernetes (chezmoi/run_onchange_after_28_krew-plugins.sh.tmpl)` |  |
| `krew:neat` | `setup-dev-linux-wsl:kubernetes (chezmoi/run_onchange_after_28_krew-plugins.sh.tmpl)` |  |
| `krew:tree` | `setup-dev-linux-wsl:kubernetes (chezmoi/run_onchange_after_28_krew-plugins.sh.tmpl)` |  |
| `krew:view-secret` | `setup-dev-linux-wsl:kubernetes (chezmoi/run_onchange_after_28_krew-plugins.sh.tmpl)` |  |
| `krew:whoami` | `setup-dev-linux-wsl:kubernetes (chezmoi/run_onchange_after_28_krew-plugins.sh.tmpl)` |  |
| `package:age` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:atuin` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:awscli` | `setup-dev-linux-wsl:cloud-aws (profiles/cloud-aws.Brewfile)` |  |
| `package:azure-cli` | `setup-dev-linux-wsl:cloud-azure (apt/vendor.list)` | signed Microsoft apt repository |
| `package:bat` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:btop` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:build-essential` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `package:containerd.io` | `setup-dev-linux-wsl:runtime-docker (apt/vendor.list)` | Docker CE from the signed Docker apt repository |
| `package:cosign` | `setup-dev-linux-wsl:security-scan (profiles/security-scan.Brewfile)` |  |
| `package:curl` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `package:direnv` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:docker-buildx-plugin` | `setup-dev-linux-wsl:runtime-docker (apt/vendor.list)` | Docker CE from the signed Docker apt repository |
| `package:docker-ce` | `setup-dev-linux-wsl:runtime-docker (apt/vendor.list)` | Docker CE from the signed Docker apt repository |
| `package:docker-ce-cli` | `setup-dev-linux-wsl:runtime-docker (apt/vendor.list)` | Docker CE from the signed Docker apt repository |
| `package:docker-compose-plugin` | `setup-dev-linux-wsl:runtime-docker (apt/vendor.list)` | Docker CE from the signed Docker apt repository |
| `package:eza` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:fastfetch` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:fd-find` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` | Homebrew formula fd |
| `package:fzf` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:g++` | `dropped:Mandrel / GraalVM via SDKMAN` | native-image build dependency |
| `package:gh` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:git` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `package:git-delta` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:git-lfs` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:gitleaks` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:gnupg` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `package:google-cloud-cli` | `setup-dev-linux-wsl:cloud-gcp (apt/vendor.list)` | signed Google apt repository |
| `package:htop` | `setup-dev-linux-wsl:productivity-extra (profiles/productivity-extra.Brewfile)` |  |
| `package:httpie` | `dropped:httpie` | xh is the HTTP client |
| `package:jq` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:just` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:kind` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `package:kubectl` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` | Homebrew formula kubernetes-cli |
| `package:kubectx` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `package:kustomize` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` |  |
| `package:libfreetype-dev` | `dropped:Mandrel / GraalVM via SDKMAN` | native-image build dependency |
| `package:libxml2-utils` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `package:mc` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` | Homebrew formula midnight-commander |
| `package:neovim` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:nmap` | `setup-dev-linux-wsl:security-scan (profiles/security-scan.Brewfile)` |  |
| `package:nvidia-container-toolkit` | `setup-dev-linux-wsl:gpu-nvidia (apt/vendor.list)` | opt-in gpu-nvidia profile |
| `package:pandoc` | `setup-dev-linux-wsl:docs (profiles/docs.Brewfile)` |  |
| `package:rclone` | `setup-dev-linux-wsl:backup (profiles/backup.Brewfile)` |  |
| `package:restic` | `setup-dev-linux-wsl:backup (profiles/backup.Brewfile)` |  |
| `package:ripgrep` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:shellcheck` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` |  |
| `package:shfmt` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` |  |
| `package:skopeo` | `setup-dev-linux-wsl:runtime-docker (profiles/runtime-docker.Brewfile)` |  |
| `package:starship` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:tmux` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:tofu` | `setup-dev-linux-wsl:cloud (profiles/cloud.Brewfile)` | Homebrew formula opentofu |
| `package:trivy` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` |  |
| `package:vim` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `package:wget` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `package:yamllint` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` |  |
| `package:zlib1g-dev` | `dropped:Mandrel / GraalVM via SDKMAN` | native-image build dependency |
| `package:zoxide` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `package:zsh` | `setup-dev-linux-wsl:base (apt/base.list)` |  |
| `repository:azure-cli` | `setup-dev-linux-wsl:cloud-azure (apt/vendor.list)` |  |
| `repository:docker` | `setup-dev-linux-wsl:runtime-docker (apt/vendor.list)` |  |
| `repository:github-cli` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` | gh comes from Homebrew, no apt source needed |
| `repository:google-cloud-cli` | `setup-dev-linux-wsl:cloud-gcp (apt/vendor.list)` |  |
| `repository:kubernetes` | `setup-dev-linux-wsl:kubernetes (profiles/kubernetes.Brewfile)` | kubectl comes from Homebrew, no apt source needed |
| `repository:nvidia-container-toolkit` | `setup-dev-linux-wsl:gpu-nvidia (apt/vendor.list)` |  |
| `repository:opentofu` | `setup-dev-linux-wsl:cloud (profiles/cloud.Brewfile)` | tofu comes from Homebrew, no apt source needed |
| `repository:trivy` | `setup-dev-linux-wsl:dev (profiles/dev.Brewfile)` | trivy comes from Homebrew, no apt source needed |
| `runtime:java:21-tem` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` | mise java temurin |
| `runtime:java:25-tem` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` | mise java temurin |
| `runtime:jvm-tool:gradle` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` |  |
| `runtime:jvm-tool:kotlin` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` |  |
| `runtime:jvm-tool:maven` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` |  |
| `runtime:mandrel` | `dropped:Mandrel / GraalVM via SDKMAN` |  |
| `runtime:node-global:corepack` | `setup-dev-linux-wsl:dev (chezmoi/dot_config/mise/config.toml.tmpl)` | pnpm = latest in mise |
| `runtime:nvm` | `dropped:nvm` | mise installs Node (node = lts) |
| `runtime:sdkman` | `dropped:sdkman` | mise installs the JVM toolchain |
| `runtime:uv` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `shell:atuin` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `shell:oh-my-zsh` | `dropped:oh-my-zsh (+ agnoster theme)` | plain zsh with git aliases |
| `shell:proxyoff` | `setup-dev-linux-wsl:core (chezmoi/dot_config/zsh/proxy.zsh)` |  |
| `shell:proxyon` | `setup-dev-linux-wsl:core (chezmoi/dot_config/zsh/proxy.zsh)` |  |
| `shell:starship` | `setup-dev-linux-wsl:core (profiles/core.Brewfile)` |  |
| `shell:zsh-autosuggestions` | `setup-dev-linux-wsl:shell-zsh (profiles/shell-zsh.Brewfile)` |  |
| `shell:zsh-syntax-highlighting` | `setup-dev-linux-wsl:shell-zsh (profiles/shell-zsh.Brewfile)` |  |
| `krew:sniff` | `dropped: setup-dev-linux-wsl ADR-010 (sniff needs packet-capture privileges in the pod)` | not carried; see ADR-010 |
| `runtime:java:21-ms` | `setup-dev-linux-wsl: mise java temurin-25 / temurin-21 (replaces the Microsoft Build of OpenJDK; ADR-014)` | operator chose Temurin |
| `runtime:java:25-ms` | `setup-dev-linux-wsl: mise java temurin-25 / temurin-21 (replaces the Microsoft Build of OpenJDK; ADR-014)` | operator chose Temurin |
