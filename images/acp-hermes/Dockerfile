# Our Hermes image = the instructor's image + our small fix (patch_acp.py)
ARG BASE_REPO=ghcr.io/nyameko/agent-control-plane-hermes
ARG BASE_DIGEST=sha256:6ec37a755e57ef868a2fcce6052535588d14742bc85df75ab973dae811f1bdda
FROM ${BASE_REPO}@${BASE_DIGEST}

# need root to edit the installed files, then switch back to the normal user
USER root
COPY patch_acp.py /tmp/patch_acp.py
RUN PKG="$(python -I -c 'import agent_control_plane, os; print(os.path.dirname(agent_control_plane.__file__))')" \
    && python -I /tmp/patch_acp.py "$PKG" \
    && python -m compileall -q "$PKG" \
    && python -I -c 'import agent_control_plane.worker, agent_control_plane.hermes_runtime' \
    && rm /tmp/patch_acp.py
USER 10001:10001
