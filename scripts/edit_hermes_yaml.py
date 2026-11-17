# Changes hermes.yaml to use our team image and adds ACP_HERMES_MIN_CONTEXT.
# It stops if something looks wrong, so we don't break the file.
import pathlib
import re
import sys

path = pathlib.Path("gitops/resources/agent-control-plane/hermes.yaml")
new_image = sys.argv[1]

# the image must be the full name with a real sha256 digest
if not re.fullmatch(r"ghcr\.io/[a-z0-9._/-]+/acp-hermes@sha256:[0-9a-f]{64}", new_image):
    sys.exit(f"STOP: '{new_image}' is not a full team image digest (did you replace <digest>?)")

text = path.read_text()
if "ACP_HERMES_MIN_CONTEXT" in text:
    sys.exit("STOP: ACP_HERMES_MIN_CONTEXT is already in hermes.yaml (already done?)")

lines = text.splitlines(keepends=True)

# swap the image line (there must be exactly one)
image_lines = [i for i, l in enumerate(lines) if l.lstrip().startswith("image:")]
if len(image_lines) != 1:
    sys.exit(f"STOP: expected exactly 1 'image:' line, found {len(image_lines)}")
i = image_lines[0]
indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
old_image = lines[i].strip()
lines[i] = f"{indent}image: {new_image}  # team image: instructor base + images/acp-hermes/patch_acp.py\n"

# add the new setting right after ACP_RUN_TIMEOUT_SECONDS, with the same spacing
timeout = [k for k, l in enumerate(lines) if l.strip() == "- name: ACP_RUN_TIMEOUT_SECONDS"]
if len(timeout) != 1:
    sys.exit(f"STOP: expected exactly 1 ACP_RUN_TIMEOUT_SECONDS entry, found {len(timeout)}")
t = timeout[0]
if not lines[t + 1].lstrip().startswith("value:"):
    sys.exit("STOP: the line after ACP_RUN_TIMEOUT_SECONDS is not its value")
name_indent = lines[t][: len(lines[t]) - len(lines[t].lstrip())]
value_indent = lines[t + 1][: len(lines[t + 1]) - len(lines[t + 1].lstrip())]
lines[t + 2:t + 2] = [
    f"{name_indent}- name: ACP_HERMES_MIN_CONTEXT\n",
    f'{value_indent}value: "4096"  # same as llm-cpu context per request\n',
]

path.write_text("".join(lines))
print(f"old image line: {old_image}")
print(f"new image line: image: {new_image}")
print("added ACP_HERMES_MIN_CONTEXT=4096 after ACP_RUN_TIMEOUT_SECONDS")
