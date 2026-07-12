#!/usr/bin/env python3
"""Deterministic HermesOS Genesis release construction and verification."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

RELEASE_ROOT_PREFIX = "HERMESOS_GENESIS_RC_v"
SOURCE_BUNDLE = "HERMESOS_GENESIS_SOURCE_BUNDLE_v0.2"
CHECKSUM_RE = re.compile(r"([0-9a-f]{64}) \*\./(.+)")
SECRET_RULES = {
    "openai_like": re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
    "github_pat": re.compile(r"(?<![A-Za-z0-9_-])gh[pousr]_[A-Za-z0-9_]{20,}"),
    "telegram_token": re.compile(r"(?<!\d)\d{8,12}:[A-Za-z0-9_-]{25,}"),
    "generic_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*[\"']?"
        r"(?!env:|vault:|\$\{|<|YOUR_|CHANGEME|REDACTED|PLACEHOLDER)"
        r"[A-Za-z0-9+/=_-]{16,}"
    ),
}
FORBIDDEN_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "state",
    "rollback",
    "prepared_profile_payload_v2",
}
FORBIDDEN_NAMES = {".env", "auth.json", "state.db", "gateway_state.json"}


class ReleaseError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_under(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(root).parts
        ),
        key=lambda p: p.as_posix(),
    )


def write_checksums(root: Path, manifest: Path, excluded: set[str]) -> None:
    records = []
    for file_path in files_under(root):
        relative = file_path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        records.append(f"{sha256(file_path)} *./{relative}")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(records) + "\n", encoding="utf-8")


def verify_checksums(root: Path, manifest: Path, excluded: set[str]) -> None:
    if not manifest.is_file():
        raise ReleaseError(f"missing checksum manifest: {manifest}")
    expected: dict[str, str] = {}
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        match = CHECKSUM_RE.fullmatch(line)
        if not match:
            raise ReleaseError(f"invalid checksum record at {manifest}:{line_number}")
        digest, relative = match.groups()
        if relative in expected:
            raise ReleaseError(f"duplicate checksum record: {relative}")
        expected[relative] = digest
    actual = {
        path.relative_to(root).as_posix(): sha256(path)
        for path in files_under(root)
        if path.relative_to(root).as_posix() not in excluded
    }
    if expected != actual:
        missing = sorted(set(actual) - set(expected))
        extra = sorted(set(expected) - set(actual))
        changed = sorted(path for path in actual.keys() & expected.keys() if actual[path] != expected[path])
        raise ReleaseError(f"checksum mismatch missing={missing} extra={extra} changed={changed}")


def is_forbidden(relative: Path) -> bool:
    parts = set(relative.parts)
    if parts & FORBIDDEN_PARTS:
        return True
    if relative.name == ".env.template":
        return False
    if relative.name in FORBIDDEN_NAMES or relative.name.endswith(".local.json"):
        return True
    return any(part.startswith(".env") for part in relative.parts)


def scan_repository(repo: Path) -> dict[str, list[str]]:
    forbidden: list[str] = []
    secrets: list[str] = []
    for path in files_under(repo):
        relative = path.relative_to(repo)
        if is_forbidden(relative):
            forbidden.append(relative.as_posix())
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, rule in SECRET_RULES.items():
            if rule.search(text):
                secrets.append(f"{relative.as_posix()}:{name}")
    if forbidden or secrets:
        raise ReleaseError(f"release gate failed forbidden={forbidden} secret_candidates={secrets}")
    return {"forbidden": forbidden, "secrets": secrets}


def seal_source_bundle(bundle: Path) -> None:
    if not (bundle / "manifest.yaml").is_file():
        raise ReleaseError(f"not a source bundle: {bundle}")
    checksum = bundle / "09_BUNDLE_METADATA" / "SHASUMS.sha256"
    write_checksums(bundle, checksum, {checksum.relative_to(bundle).as_posix()})
    verify_checksums(bundle, checksum, {checksum.relative_to(bundle).as_posix()})


def verify_source_bundle(bundle: Path) -> None:
    checksum = bundle / "09_BUNDLE_METADATA" / "SHASUMS.sha256"
    verify_checksums(bundle, checksum, {checksum.relative_to(bundle).as_posix()})


def copy_tree(source: Path, destination: Path) -> None:
    for path in files_under(source):
        relative = path.relative_to(source)
        if is_forbidden(relative):
            raise ReleaseError(f"forbidden release input: {source / relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def stage_release(repo: Path, stage: Path, version: str) -> Path:
    release_root = stage / f"{RELEASE_ROOT_PREFIX}{version}"
    release_root.mkdir(parents=True, exist_ok=True)
    required_files = ["README.md", "LICENSE", "NOTICE", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md"]
    for name in required_files:
        source = repo / name
        if not source.is_file():
            raise ReleaseError(f"missing release input: {source}")
        shutil.copy2(source, release_root / name)
    copy_tree(repo / "bootstrap", release_root / "bootstrap")
    copy_tree(repo / "design", release_root / "design")
    copy_tree(repo / "docs", release_root / "docs")
    copy_tree(repo / "source_bundle" / SOURCE_BUNDLE, release_root / "source_bundle" / SOURCE_BUNDLE)
    release_notes = repo / "release" / "NEXT_RELEASE_NOTES.md"
    if not release_notes.is_file():
        raise ReleaseError(f"missing release notes: {release_notes}")
    shutil.copy2(release_notes, release_root / "RELEASE_NOTES.md")
    metadata = {
        "schema": "hermesos.genesis.release.v0.2",
        "release": f"RC v{version}",
        "source_bundle": SOURCE_BUNDLE,
        "runtime_source_mode": "INTEGRATED",
        "archive_algorithm": "zip-deflate-fixed-metadata",
        "checksum_sealing_order": ["PACKAGE_SHASUMS.sha256", "RC_SHASUMS.sha256", "archive.sha256"],
        "upstream": "Hermes Agent / Nous Research; see NOTICE",
    }
    (release_root / "RELEASE_MANIFEST.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return release_root


def write_deterministic_zip(release_root: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files_under(release_root):
            relative = path.relative_to(release_root.parent).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(repo: Path, output: Path, version: str) -> Path:
    scan_repository(repo)
    bundle = repo / "source_bundle" / SOURCE_BUNDLE
    verify_source_bundle(bundle)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{RELEASE_ROOT_PREFIX}{version}.zip"
    sidecar = archive.with_suffix(archive.suffix + ".sha256")
    with tempfile.TemporaryDirectory(prefix="hermesos-release-") as temp:
        release_root = stage_release(repo, Path(temp), version)
        checksums = release_root / "checksums"
        package = checksums / "PACKAGE_SHASUMS.sha256"
        rc = checksums / "RC_SHASUMS.sha256"
        write_checksums(release_root, package, {"checksums/PACKAGE_SHASUMS.sha256", "checksums/RC_SHASUMS.sha256"})
        verify_checksums(release_root, package, {"checksums/PACKAGE_SHASUMS.sha256", "checksums/RC_SHASUMS.sha256"})
        write_checksums(release_root, rc, {"checksums/RC_SHASUMS.sha256"})
        verify_checksums(release_root, rc, {"checksums/RC_SHASUMS.sha256"})
        write_deterministic_zip(release_root, archive)
    sidecar.write_text(f"{sha256(archive)} *{archive.name}\n", encoding="utf-8")
    verify_release(archive, sidecar)
    return archive


def verify_release(archive: Path, sidecar: Path | None = None) -> None:
    if not archive.is_file():
        raise ReleaseError(f"release archive missing: {archive}")
    if sidecar is None:
        sidecar = archive.with_suffix(archive.suffix + ".sha256")
    if not sidecar.is_file():
        raise ReleaseError(f"release sidecar missing: {sidecar}")
    match = re.fullmatch(r"([0-9a-f]{64}) \*(.+)\n", sidecar.read_text(encoding="utf-8"))
    if not match or match.group(1) != sha256(archive) or match.group(2) != archive.name:
        raise ReleaseError("release archive SHA-256 verification failed")
    with tempfile.TemporaryDirectory(prefix="hermesos-verify-") as temp:
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
                raise ReleaseError("unsafe archive member")
            zf.extractall(temp)
        roots = [path for path in Path(temp).iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise ReleaseError("release archive has an invalid root layout")
        root = roots[0]
        verify_checksums(root, root / "checksums" / "PACKAGE_SHASUMS.sha256", {"checksums/PACKAGE_SHASUMS.sha256", "checksums/RC_SHASUMS.sha256"})
        verify_checksums(root, root / "checksums" / "RC_SHASUMS.sha256", {"checksums/RC_SHASUMS.sha256"})
        verify_source_bundle(root / "source_bundle" / SOURCE_BUNDLE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("scan", "seal-source", "verify-source", "build", "verify-release"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--version", default="0.2")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "scan":
            print(json.dumps(scan_repository(args.repo), sort_keys=True))
        elif args.command == "seal-source":
            seal_source_bundle(args.bundle or args.repo / "source_bundle" / SOURCE_BUNDLE)
        elif args.command == "verify-source":
            verify_source_bundle(args.bundle or args.repo / "source_bundle" / SOURCE_BUNDLE)
        elif args.command == "build":
            if args.out is None:
                raise ReleaseError("--out is required for build")
            print(build(args.repo, args.out, args.version))
        else:
            if args.archive is None:
                raise ReleaseError("--archive is required for verify-release")
            verify_release(args.archive)
    except ReleaseError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
