# Fix for the given Hermes image.
# It changes 3 small things so Hermes works with our CPU model:
#   1. turn off "lazy installs" in Hermes' config (it tries to pip install boto3 and hangs)
#   2. pass HERMES_DISABLE_LAZY_INSTALLS=1 and ACP_HERMES_MIN_CONTEXT to Hermes
#   3. let us lower Hermes' 64K context minimum (only if ACP_HERMES_MIN_CONTEXT is set)
import pathlib
import sys

pkg = pathlib.Path(sys.argv[1])


def patch(path, old, new):
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        sys.exit(f"PATCH FAILED: expected 1 match in {path.name}, found {count}:\n{old}")
    path.write_text(text.replace(old, new))
    print(f"patched {path.name}")


worker = pkg / "worker.py"
runtime = pkg / "hermes_runtime.py"

# 1. add "allow_lazy_installs: false" to the config Hermes gets
patch(
    worker,
    'memory:\n  memory_enabled: false\n  user_profile_enabled: false\n"""',
    'memory:\n  memory_enabled: false\n  user_profile_enabled: false\n'
    'security:\n  allow_lazy_installs: false\n"""',
)

# 2. pass the two settings on to the Hermes sub-process
patch(
    worker,
    '"HERMES_ENABLE_PROJECT_PLUGINS": "0",\n',
    '"HERMES_ENABLE_PROJECT_PLUGINS": "0",\n'
    '            "HERMES_DISABLE_LAZY_INSTALLS": "1",\n'
    '            "ACP_HERMES_MIN_CONTEXT": os.environ.get("ACP_HERMES_MIN_CONTEXT", ""),\n',
)

# 3. lower the 64K minimum, but only when ACP_HERMES_MIN_CONTEXT is set
patch(
    runtime,
    "    from run_agent import AIAgent\n",
    "    from run_agent import AIAgent\n"
    "\n"
    "    # our fix: this run has no tools, so the 64K minimum isn't needed\n"
    "    floor = os.environ.get(\"ACP_HERMES_MIN_CONTEXT\", \"\").strip()\n"
    "    if floor:\n"
    "        floor = int(floor)\n"
    "        if not 2048 <= floor <= 64000:\n"
    "            raise RuntimeError(\"ACP_HERMES_MIN_CONTEXT must be 2048-64000\")\n"
    "        import agent.agent_init as _agent_init\n"
    "        _agent_init.MINIMUM_CONTEXT_LENGTH = floor\n",
)
