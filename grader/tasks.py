import os
import subprocess
import tempfile
import boto3
from celery import shared_task
from django.conf import settings
import requests
import uuid
import shutil
import resource


s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("AWS_S3_ENDPOINT"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION"),
)


def run_cpp_code(source_code, input_data, time_limit, memory_limit):
    with tempfile.TemporaryDirectory() as tmpdir:
        code_path = os.path.join(tmpdir, "main.cpp")
        binary_path = os.path.join(tmpdir, "main")

        with open(code_path, "w") as f:
            f.write(source_code)

        compile_result = subprocess.run(
            ["g++", code_path, "-o", binary_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        if compile_result.returncode != 0:
            return "CE", compile_result.stderr.decode()

        try:
            memory_kb = memory_limit * 1024
            cmd = f"ulimit -v {memory_kb} && ./main"

            proc = subprocess.run(
                cmd,
                shell=True,
                input=input_data.encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=time_limit,
                cwd=tmpdir,
            )

            stderr_output = proc.stderr.decode().lower()
            if "killed" in stderr_output or "memory" in stderr_output:
                return "MLE", stderr_output

            return "OK", proc.stdout.decode()

        except subprocess.TimeoutExpired:
            return "TLE", ""

        except Exception as e:
            return "RE", str(e)

def set_limits(memory_bytes):
    def inner():
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    return inner

def run_cpp_code_sandboxed(source_code: str, input_data: str, time_limit: int, memory_limit: int):
    temp_dir = f"/tmp/grader_{uuid.uuid4().hex}"
    os.makedirs(temp_dir, exist_ok=True)

    cpp_path = os.path.join(temp_dir, "main.cpp")
    exe_path = os.path.join(temp_dir, "main")
    input_path = os.path.join(temp_dir, "input.txt")
    output_path = os.path.join(temp_dir, "output.txt")

    try:
        with open(cpp_path, "w") as f:
            f.write(source_code)
        with open(input_path, "w") as f:
            f.write(input_data)

        compile_proc = subprocess.run(
            ["g++", cpp_path, "-o", exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        if compile_proc.returncode != 0:
            return "CE", compile_proc.stderr.decode()

        with open(input_path, "rb") as f_in, open(output_path, "wb") as f_out:
            run_proc = subprocess.run(
                [exe_path],
                stdin=f_in,
                stdout=f_out,
                stderr=subprocess.PIPE,
                timeout=time_limit,
                preexec_fn=set_limits(memory_limit * 1024 * 1024)
            )

        with open(output_path, "r") as f:
            return "OK", f.read().strip()

    except subprocess.TimeoutExpired:
        return "TLE", ""

    except MemoryError:
        return "MLE", "Memory limit exceeded."

    except Exception as e:
        return "RE", str(e)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def list_testcases(bucket, problem_id):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=f"problems/{problem_id}/testcase_")
    inputs, outputs = [], []

    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".in"):
            inputs.append(key)
        elif key.endswith(".out"):
            outputs.append(key)

    inputs.sort()
    outputs.sort()
    return list(zip(inputs, outputs))


@shared_task(name="grade_submission", queue="grading")
def grade_submission(submission_id):
    from grader.models import Submission

    sub = Submission.objects.get(id=submission_id)
    if sub.language != "cpp":
        return

    bucket = "infinitys"
    testcases = list_testcases(bucket, sub.problem_id)

    result = []

    for idx, (in_key, out_key) in enumerate(testcases, 1):
        input_data = s3.get_object(Bucket=bucket, Key=in_key)["Body"].read().decode()
        expected_output = (
            s3.get_object(Bucket=bucket, Key=out_key)["Body"].read().decode().strip()
        )

        status, output = run_cpp_code_sandboxed(
            sub.code_content,
            input_data,
            time_limit=sub.time_limit,
            memory_limit=sub.memory_limit,
        )

        if status == "OK":
            status = "AC" if output.strip() == expected_output else "WA"

        result.append({"testcase": idx, "status": status})

    # Gửi về webhook
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        requests.post(
            webhook_url,
            json={
                "problem_id": sub.problem_id,
                "submission_id": sub.id,
                "result": result,
                "raw": {
                    "status": status,
                    "output": output.strip(),
                }
            },
        )
