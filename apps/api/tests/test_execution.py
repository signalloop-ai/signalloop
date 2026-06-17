import json
from io import BytesIO

from signalloop_api.execution import ECSFargateExecutionProvider


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket: str, Key: str) -> dict:
        return {"Body": BytesIO(self.objects[(Bucket, Key)])}


class FakeWaiter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def wait(self, **kwargs) -> None:
        self.calls.append(kwargs)


class FakeECS:
    def __init__(self) -> None:
        self.waiter = FakeWaiter()
        self.run_task_calls: list[dict] = []

    def run_task(self, **kwargs) -> dict:
        self.run_task_calls.append(kwargs)
        return {"tasks": [{"taskArn": "arn:aws:ecs:region:123:task/abc"}], "failures": []}

    def get_waiter(self, name: str) -> FakeWaiter:
        assert name == "tasks_stopped"
        return self.waiter

    def describe_tasks(self, **kwargs) -> dict:
        return {"tasks": [{"containers": [{"name": "runner", "exitCode": 0}]}]}


def test_ecs_fargate_provider_writes_payload_runs_task_and_reads_result(monkeypatch) -> None:
    fake_s3 = FakeS3()
    fake_ecs = FakeECS()

    def fake_client(service_name: str, region_name: str):
        assert region_name == "us-east-1"
        if service_name == "ecs":
            return fake_ecs
        if service_name == "s3":
            return fake_s3
        raise AssertionError(service_name)

    monkeypatch.setattr("boto3.client", fake_client)
    monkeypatch.setattr("signalloop_api.execution.settings.aws_region", "us-east-1")
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_cluster", "signalloop")
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_runner_task_definition", "runner-task")
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_runner_container", "runner")
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_subnet_ids", ["subnet-1"])
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_security_group_ids", ["sg-1"])
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_assign_public_ip", "DISABLED")
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_waiter_delay_seconds", 1)
    monkeypatch.setattr("signalloop_api.execution.settings.aws_ecs_waiter_max_attempts", 2)
    monkeypatch.setattr("signalloop_api.execution.settings.signalloop_run_bucket", "runs-bucket")

    provider = ECSFargateExecutionProvider()
    output_keys = [key for bucket, key in fake_s3.objects if key.endswith("/output.json")]
    assert output_keys == []

    original_put_object = fake_s3.put_object

    def put_object_and_seed_output(Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        original_put_object(Bucket, Key, Body, ContentType)
        if Key.endswith("/input.json"):
            output_key = Key.replace("/input.json", "/output.json")
            original_put_object(
                Bucket,
                output_key,
                json.dumps(
                    {
                        "status": "passed",
                        "exit_code": 0,
                        "stdout": "ok",
                        "stderr": "",
                        "duration_ms": 50,
                    }
                ).encode("utf-8"),
                "application/json",
            )

    fake_s3.put_object = put_object_and_seed_output  # type: ignore[method-assign]

    result = provider.run_public({"tests/test_sample.py": "def test_sample():\n    assert True\n"})

    assert result["status"] == "passed"
    assert fake_ecs.run_task_calls
    run_task_call = fake_ecs.run_task_calls[0]
    assert run_task_call["cluster"] == "signalloop"
    assert run_task_call["taskDefinition"] == "runner-task"
    override_env = run_task_call["overrides"]["containerOverrides"][0]["environment"]
    assert {item["name"] for item in override_env} == {
        "SIGNALLOOP_RUNNER_INPUT",
        "SIGNALLOOP_RUNNER_OUTPUT",
    }
    input_object = next(body for (bucket, key), body in fake_s3.objects.items() if key.endswith("/input.json"))
    assert json.loads(input_object.decode("utf-8"))["command"] == ["python", "-m", "pytest", "tests"]
