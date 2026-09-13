# Running this repo on the Alliance cluster (Nibi)

Everything the campaign does is "start one vLLM server on one GPU, send it
one request, read `/metrics`, stop it" — driven by plain bash/Python on a
single box. On the cluster that maps to **one sbatch job = one H100 for N
hours running `scripts/campaign_run.py` exactly as on the old box**, with
the server and client on the same node. No code changes were needed; this
directory holds the environment recipe and job templates.

## Account facts (from CCDB, 2026-09-11)

| | |
|---|---|
| username | `billxby` (CCI dzn-991), sponsored by Prof. Zhang's CCRI `dqh-742-01` |
| Slurm account, general-purpose clusters | **`def-hongyanz`** (RAP dqh-742-aa, 8 active allocations) |
| Slurm account, AI clusters (Killarney / Vulcan / TamIA) | `aip-hongyanz` (RAP dqh-742-ac, PAICE) |
| cluster targeted here | Nibi, `nibi.alliancecan.ca` (Waterloo, H100s; successor of Graham) |
| local shortcut | `ssh nibi` (`~/.ssh/config` on Bill's Mac: user, key, connection multiplexing) |
| MFA | Duo push to iPhone, option `1` at the prompt; one push per multiplexed master, ~10 min reuse |

**Root cause found 2026-09-11 (evening, CCDB checked in the browser):**
CCDB -> Resources -> *Access Systems* (`https://ccdb.alliancecan.ca/me/access_systems`)
shows every system as **"Not responded"** (HPC: Fir, HPSS, Narval, Nibi,
Rorqual, Trillium; Cloud: all; AI: Killarney, TamIA, Vulcan; Quantum).
Cluster access is per-system and opt-in: nothing is provisioned on a
cluster until "I request access" is selected for it there. Key + Duo pass
because they are checked against the CCDB identity, not the per-cluster
access flag, which is exactly the table below. Docs
(`https://docs.alliancecan.ca/wiki/Nibi/en#Access`): "Select Nibi from the
list on the left. Select I request access. It can take up to one hour for
your access to be enabled." Narval/Rorqual additionally require accepting
the Calcul Québec consent + SLA + Terms of Use on the same page.
**Fix:** select "I request access" for Nibi (def-hongyanz) and Killarney
(aip-hongyanz), wait up to 1 h, `ssh nibi`. No support ticket needed; the
status table and ticket draft below are superseded.

**Status 2026-09-11 (end of day):** the account is not usable on ANY
cluster yet, and it is not a Nibi problem:

| cluster | public key | Duo | then |
|---|---|---|---|
| nibi.alliancecan.ca | accepted | Success (5 separate times over 3 h) | `Connection closed by 199.241.160.0 port 22` before a shell starts |
| fir.alliancecan.ca | accepted | Success | `Connection closed by 206.12.125.2 port 22` before a shell starts |
| killarney.alliancecan.ca (aip-hongyanz) | accepted | Success | `Connection closed by 142.1.173.40 port 22` before a shell starts |
| rorqual.alliancecan.ca | accepted | Success x3 (re-prompted each time) | `Permission denied (keyboard-interactive,hostbased)` |
| narval.alliancecan.ca | accepted | Success x3 (re-prompted each time) | `Permission denied (keyboard-interactive,hostbased)` |

CCDB (checked by Bill 2026-09-11) lists `def-hongyanz` on Fir, Narval,
Nibi, Rorqual, Trillium and `aip-hongyanz` GPU on Killarney, Tamia, Vulcan
(to 2030) — so the *rights* exist everywhere, and the *accounts* on the
machines do not. The two failure shapes are what an un-provisioned account
looks like under two sites' PAM setups: the key is looked up in CCDB by
username (so it works), Duo is per-username (so it works), and then either
the account/session stage refuses (Rorqual/Narval: PAM retries the
second factor three times, then denies) or the session cannot be set up
(Nibi/Fir/Killarney: no home directory / user entry, connection dropped
without a disconnect reason). Status pages showed no outage. Three days
after the CCDB role was approved (2026-09-08), this is not a transient
lag. Two things to do, in this order:

1. In CCDB (`https://ccdb.alliancecan.ca`): look for any banner or pending
   item — updated Terms of Use / policy acceptance, an unconfirmed email,
   or a role still marked pending. Anything unaccepted there can block
   cluster logins after MFA with exactly these symptoms.
2. Email `support@tech.alliancecan.ca` (subject "Cluster login fails after
   successful MFA — billxby"):

   > Username billxby (CCI dzn-991, role dzn-991-01 approved 2026-09-08,
   > sponsored by dqh-742-01; member of def-hongyanz and aip-hongyanz).
   > Public-key auth and Duo MFA both succeed on every cluster, but I
   > cannot get a session on any of them. Nibi, Fir and Killarney print
   > "Success. Logging you in..." and then "Connection closed by <ip>
   > port 22" before a shell starts (Nibi 199.241.160.0, Fir 206.12.125.2,
   > Killarney 142.1.173.40; reproduced repeatedly on 2026-09-11 between
   > 12:00 and 16:00 ET from IP <your IP>). Rorqual and Narval re-prompt
   > Duo three times, each "Success", then "Permission denied
   > (keyboard-interactive,hostbased)". With ssh -v on Nibi, the line
   > immediately after Duo's "Success. Logging you in..." is "debug1:
   > Authentications that can continue: keyboard-interactive,hostbased"
   > (no "Authentication succeeded"), i.e. the keyboard-interactive
   > authentication is being rejected by the PAM stack after the Duo step
   > on every cluster. My SSH key was added to CCDB on 2026-09-11 11:35 ET
   > and Duo was enrolled the same day. Could you check whether my account
   > is fully activated for cluster access (LDAP/access-policy state, any
   > required acknowledgement I may be missing in CCDB), or whether my
   > record is blocking activation?

   The `ssh -v` transcript is at `/tmp/nibi_diag.log` on Bill's Mac (attach
   lines 60-80 to the ticket).

Also worth asking Chiatzen how his access was activated and which cluster
the group actually uses (`aip-hongyanz` suggests Killarney/Vulcan, which
may activate separately).

Ask Chiatzen which cluster the group actually runs on: the `aip-` RAP
suggests Zhang's AI allocation lives on Killarney/Vulcan, which have far
more GPU headroom than Nibi's shared pool. The scripts here take the
account and GPU type as variables for that reason.

## First login done 2026-09-11 (evening) — the facts

Access enabled ~1 h after requesting it in CCDB; `ssh nibi` now lands on
`l4.nibi.sharcnet`. What the checklist returned:

| | |
|---|---|
| Slurm accounts (`sshare -U`) | `def-hongyanz_cpu`, `def-hongyanz_gpu` (QOS `interac`, `normal`) — use **`--account=def-hongyanz_gpu`** for GPU jobs |
| groups | `def-hongyanz`, `rrg-hongyanz`, `aip-hongyanz`, `inst_uwaterloo`, `ontario_users` |
| H100 nodes | `g1`–`g28`: `gpu:h100:8`, 112 cores, 2 TB RAM; `--gpus-per-node=h100:1` is correct. Also MIG-sliced H100 nodes (`g30`–`g37`), one A100 node, MI300A nodes, T4s |
| partitions | auto-selected by Slurm from walltime (`gpubase_interac`, `gpubase_bygpu_b1..b5`, `gpubackfill`, …) — do not set `--partition` |
| GPU node driver | 580.82.07 (CUDA 13.0-capable) on `g1` — cu129 wheels are fine |
| compute-node internet | **yes** (pypi/HF reachable from `g1`); `HF_HUB_OFFLINE=1` in jobs is just a guard |
| node-local scratch | `$SLURM_TMPDIR` = `/localscratch/<user>.<jobid>.0`, 11 TB free |
| storage | home 50 GiB; scratch `/scratch/billxby` 1 TiB; project `/project/6071935` (= `~/projects/def-hongyanz`) 58/931 GiB used |
| modules | `StdEnv/2023 python/3.12 cuda/12.9` (also python 3.10–3.14, cuda 12.2/12.6/13.2, apptainer 1.2.4); **only in a login shell** (`bash -l`) — a bare `ssh nibi cmd` does not load them |
| pip | the python module sets `PIP_CONFIG_FILE` to the Alliance wheelhouse config; `setup_nibi.sh` overrides it to `/dev/null` so the pinned PyPI / PyTorch-cu129 / vLLM-index wheels are used |
| repo on cluster | `~/projects/def-hongyanz/billxby/lossy-token-eff` (rsynced from the Mac, `.git` excluded at 3.6 GB) |

## First-login checklist (5 minutes, do once)

```bash
sshare -U                      # confirm def-hongyanz is listed; note any _gpu/_cpu suffixes
sinfo -o "%P %G %D %t" | grep -i gpu   # GPU partitions/gres names -> fixes GPU_TYPE below
diskusage_report               # home / project / scratch quotas
module spider python cuda      # exact module versions -> fixes setup_nibi.sh
ls -la ~/projects/             # symlink to def-hongyanz should exist
```

Then `bash cascade/cluster/nibi_interactive.sh` for a 1-hour GPU shell and
`nvidia-smi` on it: the **driver version decides the wheel flavour** (driver
>= 580 -> the default cu130 torch/vLLM wheels are fine; older -> use the
cu129 wheels exactly as `remote/ENVIRONMENT.md` did).

## Layout on the cluster

| what | where | why |
|---|---|---|
| repo + venvs | `~/projects/def-hongyanz/billxby/lossy-token-eff` | project space: large quota, not purged, shared with the group |
| HF model cache | `~/projects/def-hongyanz/billxby/hf` | 13G target + 0.7G drafter (GPT-OSS), 16G + small (Qwen3); pre-downloaded on the login node |
| runs/ logs/ | inside the repo (default `--runs-root`) | ~25 KB per run without traces; keep in project so `campaign_report.py` finds them; move to `$SCRATCH` only if traces are on |
| vLLM / Triton compile caches | `$SLURM_TMPDIR` (node-local) | fast, cleaned per job, never counts against quota |
| `/tmp` knob files | node-local `/tmp` of the job's node | the sampler reads them; server and client share the node, so nothing changes |

Home (`~`) has a small quota — do not put the venv there.

## Environment build (login node, once): `setup_nibi.sh`

Mirrors `remote/ENVIRONMENT.md` (vLLM 0.26.0 + torch 2.11 cu129, then a
matplotlib venv for reporting) with `pip` instead of `uv`, and downloads
the four checkpoints into the project HF cache. Read the script's header:
three variables (`MODULES`, `WHEEL_FLAVOUR`, `PROJECT_DIR`) must match what
the first-login checklist showed. Compute nodes may have no internet, so
every download happens here, and jobs run with `HF_HUB_OFFLINE=1`.

If the vLLM wheel imports but crashes on this glibc/toolchain, the fallback
is Apptainer with the official `vllm/vllm-openai:v0.26.0` image; the patches
apply the same way inside the container's site-packages. Not tried.

## Patches on the cluster

`patches/apply.sh` uses GNU `sha256sum` and `cp --remove-destination`, both
present on Linux. `pip` does not hardlink like `uv` does, so the hardlink
trap in `remote/ENVIRONMENT.md` does not apply, but the script's safe path
is still the right one. The campaign runner switches patches automatically
between arms.

**Qwen3 caveat:** Qwen3-8B uses vLLM's V2 runner, whose consolidated
multi-method file exists only on the old box (see `../DIRECTIONS.md` D8).
A fresh install here has a pristine V2, which `apply.sh` accepts — so every
Qwen3 arm would silently run strict. **Do not run `*_qwen3` datasets here
until that file is recovered and committed as a patch.** GPT-OSS-20B (V1)
is fully reproducible from the repo.

## Submitting experiments by id: `cascade/run.sh --target nibi`

`bash cascade/run.sh E1-gsm8k --target nibi` builds the exact command for
that experiment (`../EXPERIMENTS.md`) and submits it through
`nibi_run.sbatch`, a generic one-GPU wrapper that loads the modules, sets
the offline HF cache and node-local compile caches, picks a port from the
job id, and runs the command from the repo root. `--dry-run` shows the
command without submitting. `nibi_campaign.sbatch` below is the same
wrapper specialised to a single `campaign_run.py` call, kept for hand use.

## Submitting: `nibi_campaign.sbatch`

```bash
sbatch cascade/cluster/nibi_campaign.sbatch gsm8k spec_casc_tok_lt 30 3   # dataset, method(s), full cases, calib cases
squeue -u $USER ; tail -f casc-<jobid>.out
```

One GPU, 8 CPUs, 64 GB, 12 h by default (edit the `#SBATCH` lines; shorter
walltime = faster scheduling). The job loads the modules, activates nothing
(scripts use `.venv-vllm/bin/python` by absolute path), points caches at
`$SLURM_TMPDIR`, picks a port from the job id so two jobs on one node
cannot collide, runs `campaign_run.py`, then `campaign_report.py`. Runs are
skip-if-done, so resubmitting after a walltime kill just continues.

Budget guide from the campaign's timings: gsm8k 30 cases x 2 methods x
(4-point calibration on 3 cases + 3 alphas) ~= 1-2 h; aime24 the same
shape ~= 6-8 h. Ask for `--time` accordingly; Nibi's queue favours short
jobs.

## Syncing code: `sync_to_nibi.sh`

`git clone` the repo on the cluster once (it has an `origin` remote), then
push/pull as usual. For quick iteration without commits, `bash
cascade/cluster/sync_to_nibi.sh` rsyncs the working tree (excluding runs,
logs, venvs and `.git`) to the project directory. Results come back the
other way: `rsync -avz nibi:projects/def-hongyanz/billxby/lossy-token-eff/campaign/ campaign/`.

## Interactive debugging: `nibi_interactive.sh`

`salloc` for one H100 for a short window; then inside it, the same
commands as the old box (`remote/run_server_vllm.sh` by hand, or a
3-case `campaign_run.py --dry-run`). Interactive allocations are for
debugging, not sweeps.
