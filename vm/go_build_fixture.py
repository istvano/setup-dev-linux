"""Synthetic offline Go workflow for the dedicated guest acceptance suite."""
from pathlib import Path
import os
import subprocess


def check(fixture):
    root = fixture / 'go-build'
    root.mkdir()
    (root / 'answer.go').write_text(
        'package answer\n\nfunc Value() int { return 6 * 7 }\n')
    (root / 'answer_test.go').write_text(
        'package answer\n\nimport "testing"\n\n'
        'func TestValue(t *testing.T) { if Value() != 42 { t.Fatal(Value()) } }\n')
    command = r'''
set -e
cd "$1"
go version | grep -F 'go1.27.1 linux/amd64'
test "$(go env GOOS GOARCH)" = $'linux\namd64'
go mod init example.invalid/offline-fixture
GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local go test ./...
mkdir cmd
cat > cmd/main.go <<'EOF'
package main
import (
  "fmt"
  answer "example.invalid/offline-fixture"
)
func main() { fmt.Println(answer.Value()) }
EOF
GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local go build -o fixture-bin ./cmd
test "$(./fixture-bin)" = 42
'''
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(('GOENV', 'GOFLAGS', 'GONOSUMDB', 'GONOPROXY',
                               'GOPRIVATE', 'GOTOOLCHAIN', 'GOWORK'))
    }
    environment.update(GOPROXY='off', GOSUMDB='off', GOTOOLCHAIN='local')
    result = subprocess.run(
        ['zsh', '-i', '-c', command, '--', str(root)], env=environment,
        capture_output=True, text=True, timeout=180)
    if result.returncode:
        print(result.stdout[-4000:])
        print(result.stderr[-2000:])
        raise AssertionError('Go build fixture failed')
    assert (root / 'fixture-bin').read_bytes().startswith(b'\x7fELF')
    print('PASS: Go 1.27.1 local module test/build/run with network-disabled module settings')
