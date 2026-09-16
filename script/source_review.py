"""Render the pre-build evidence ledger; never resolve or download software."""


def render_source_review(ledger):
    records = ledger['records']
    artifacts = [a for r in records for a in r['artifacts']]
    extensions = [r for r in records if 'extension_manifest' in r]
    out = [
        '# Linux delivery source review', '',
        f'Observation date: {ledger["reviewed_at"]}. Generated from',
        '[source-review.json](../catalogue/source-review.json). This is a pre-build',
        'evidence ledger, **not an executable installation lock or delivery approval**.', '',
        f'Coverage: **{len(records)} selected package/extension capabilities**,',
        f'**{len(artifacts)} artifact candidates**, **{len(extensions)} inspected extension roots**.',
        'Behavior/manual capabilities do not need artifact rows. Optional, pending and omitted',
        'capabilities remain outside the selected delivery review.', '',
        '## How to interpret the evidence', '',
        '- `published-only`: a primary publisher/index supplies a digest; artifact bytes have not been checked.',
        '- `cached-apt-metadata`: a trusted Ubuntu origin was observed in the local APT cache; this is not an end-to-end signature/package check.',
        '- `downloaded-observed`: downloaded bytes were hashed; no independent published digest was compared.',
        '- `downloaded-matched-published`: downloaded bytes matched the publisher digest.',
        '- `missing-digest`: the candidate cannot become an integrity lock yet.', '',
        'Metadata evidence includes its source URL and the SHA-256 of the observed response.',
        'Licence labels are observations from publisher/source or installed-package metadata.',
        'A HEAD licence file does not prove the terms of a different tagged binary or bundled',
        'components. All records retain review-required status and explicit remaining work.',
        'The catalogue therefore continues to report delivery as unverified.', '',
        'APT candidates use the observed resolute, resolute-updates or resolute-security suites.',
        'Package versions are observations, not permanent security-update freezes. Proposed',
        'upstream sources for packages missing from APT need a deliberate source/policy change',
        'before installation. Ghostty was found in Ubuntu package metadata; do not use a',
        'community installer merely because the old candidate assumed an upstream download.', '',
        'Simple Scan and SANE utilities were identified from installed package metadata.',
        'This resolves the scanner group names, not physical-device/backend readiness.', '',
        'Extension ZIP package manifests were inspected without executing them. Root IDs and',
        'versions must agree with Marketplace metadata. Dependency/pack children are recorded',
        'separately and still require review; they must not be silently accepted as root coverage.', '',
        'See [pre-build review](PRE-BUILD-REVIEW.md) for decisions and principal blockers.', '',
        '## Selected artifact candidates', '',
        '| Capability | Proposed source | Observed version(s) | Integrity evidence |',
        '|---|---|---|---|',
    ]
    for row in records:
        versions = ', '.join(dict.fromkeys(a['version'] for a in row['artifacts'])) or 'Unresolved / supplied by another capability'
        checks = ', '.join(sorted({a['verification'] for a in row['artifacts']})) or 'No artifact'
        out.append(f'| `{row["capability_id"]}` | {row["proposed_channel"]} | {versions.replace("|", " / ")} | {checks} |')
    out += ['', '## Extension dependency review', '', '| Root | Required dependencies | Pack children |', '|---|---|---|']
    for row in extensions:
        manifest = row['extension_manifest']
        dependencies = ', '.join(manifest['dependencies']) or 'None declared'
        children = ', '.join(manifest['pack']) or 'None declared'
        out.append(f'| `{row["capability_id"].removeprefix("extension-")}` | {dependencies} | {children} |')
    return '\n'.join(out) + '\n'
