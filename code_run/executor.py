import logging
from pathlib import Path

from runbox import SandboxBuilder, DockerExecutor
from runbox.models import DockerProfile, File

from code_run.models import RunCodeTask, RunResult
from code_run.settings import settings


def generate_builder(
    task: RunCodeTask,
) -> SandboxBuilder:
    meta = settings.languages[task.language]
    version_conf = meta.versions[task.language_version]
    builder = (
        SandboxBuilder()
        .with_limits(settings.limits)
        .with_profile(
            DockerProfile(
                image=version_conf.image,
                cmd_template=version_conf.command,
                workdir=Path("/sandbox"),
                user="sandbox",
            )
        )
        .add_files(
            File(
                name=meta.file_name,
                content=task.code,
            )
        )
    )

    return builder


async def execute(task: RunCodeTask, executor: DockerExecutor) -> RunResult:
    builder = generate_builder(task)

    async with await builder.create(executor) as sandbox:
        logging.info(f"Created {task.language} sandbox {sandbox.name}")
        await sandbox.run(stdin=task.stdin.encode())
        logging.info(f"Ran {task.language} sandbox {sandbox.name}")
        await sandbox.wait()
        logs = await sandbox.log(stderr=True, stdout=True)
        state = await sandbox.state()
        logging.info(
            f"{task.language} sandbox {sandbox.name} finished "
            f"{state.exit_code=} {state.duration.total_seconds()=}"
        )
        return RunResult(
            correlation_id=task.correlation_id,
            reply_to=task.reply_to,
            ok=(state.exit_code == 0),
            time_limit=state.cpu_limit,
            memory_limit=state.memory_limit,
            execution_time=state.duration.total_seconds(),
            runtime_error=(state.exit_code != 0),
            logs=logs,
        )
