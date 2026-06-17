# Render Docker Runtime Probe

This is a throwaway deployment probe for the SignalLoop worker hosting decision.

SignalLoop's execution worker currently requires a runtime that can start Docker containers from inside the running worker service. Render supports deploying services from Dockerfiles, but that is not the same as guaranteeing that the running service can execute `docker run`.

## What this checks

Deploy this directory as a Render Docker web service, then open:

```text
https://<your-render-service>.onrender.com/probe
```

The result reports:

- whether the Docker CLI exists in the runtime image,
- whether `/var/run/docker.sock` exists and is readable/writable,
- whether `docker version` succeeds,
- whether `docker run --rm hello-world` succeeds.

## Expected interpretation

- If `docker_run_hello_world.ok` is `true`, Render can likely host the current SignalLoop worker architecture.
- If `docker_run_hello_world.ok` is `false`, do not host the current worker on Render without changing the worker architecture or using a different runtime.

## Render setup

Create a new Render Web Service:

- Runtime: `Docker`
- Dockerfile Path: `tools/render-docker-probe/Dockerfile`
- Root Directory: repository root, unless Render asks for the service root
- Plan: any temporary test plan

Delete the service after the probe.
