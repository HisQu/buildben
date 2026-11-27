# Backlog

GitHub Issues hold durable work. This file orders planned Passes and keeps
Deferred work at the end. Follow the [issues and backlog rules](CONTRIBUTING.md#issues-and-backlog).


<br>

---

<br>

## Table Of Contents

1. [Backlog](#backlog)
   1. [Table Of Contents](#table-of-contents)
2. [Planned Pass 1 — Release payload cache filtering](#planned-pass-1--release-payload-cache-filtering)
   1. [P2 / E2 \[Tooling\] - *Exclude interpreter caches from release payloads*](#p2--e2-tooling---exclude-interpreter-caches-from-release-payloads)
3. [Deferred](#deferred)
   1. [P3 / E2 \[Tooling\] - *Native installation proof remains pending*](#p3--e2-tooling---native-installation-proof-remains-pending)

<br>

---

<br>



# Planned Pass 1 — Release payload cache filtering

## P2 / E2 [Tooling] - *Exclude interpreter caches from release payloads*
- **Issue:** https://github.com/HisQu/buildben/issues/8
- **Area:** `src/buildben_dev/packaging/release_stage.py`
- **Observed while:** restaging the 0.13.0 installer.
- **Evidence:** local restaging included interpreter caches absent from the published bundle.
- **Why not fixed now:** the published bundle is correct.
- **Suggested next step:** exclude interpreter caches, extend the existing release-asset regression and check the parallel PersoDB stager.

<br>

# Deferred

## P3 / E2 [Tooling] - *Native installation proof remains pending*
- **Issue:** https://github.com/HisQu/buildben/issues/9
- **Area:** `.github/workflows/ci.yml`, `tests/test_release_install.py`, `tests/test_lifecycle.py`
- **Observed while:** implementing the AppRC-backed installation lifecycle from WSL.
- **Evidence:** Linux checks leave native Windows and macOS behavior unverified.
- **Why not fixed now:** native verification is explicitly deferred.
- **Suggested next step:** follow the [Windows procedure](README.md#windows-installer-verification-procedure) and [Unix staging procedure](README.md#unix-installer-staging-verification) when native-platform work is authorized.
