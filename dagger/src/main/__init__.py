import asyncio

import dagger
from dagger import dag, function, object_type
from jinja2 import Template


DEVELOP_VERSION = "0.1.0-develop"

@object_type
class IbidemApi:
    @function
    def deps(self, source: dagger.Directory, platform: dagger.Platform | None = None) -> dagger.Container:
        """Install dependencies in a container"""
        return (
            dag.container(platform=platform)
            .from_("ghcr.io/astral-sh/uv:python3.12-bookworm-slim")
            .with_workdir("/app")
            .with_file("/app/pyproject.toml", source.file("pyproject.toml"))
            .with_file("/app/uv.lock", source.file("uv.lock"))
            .with_file("/app/README.rst", source.file("README.rst"))
            .with_new_file("/app/ibidem_api/__init__.py", f"VERSION = \"0.0.1+ignore\"")
            .with_exec(["uv", "sync", "--no-install-project", "--no-editable"])
        )

    @function
    def build(self, source: dagger.Directory, platform: dagger.Platform | None = None, version: str = DEVELOP_VERSION) -> dagger.Container:
        """Build the application"""
        return (
            self.deps(source, platform)
            .with_directory("/app/ibidem_api", source.directory("ibidem_api"))
            .with_new_file("/app/ibidem_api/__init__.py", f"VERSION = \"1.{version.replace("-", "+")}\"")
            .with_exec(["uv", "sync", "--frozen", "--no-editable"])
        )

    @function
    def docker(self, source: dagger.Directory, platform: dagger.Platform | None = None, version: str = DEVELOP_VERSION) -> dagger.Container:
        """Build the Docker container"""
        build = self.build(source, platform, version)
        return (
            dag.container(platform=platform)
            .from_("python:3.12-slim")
            .with_workdir("/app")
            .with_directory("/app/.venv", build.directory("/app/.venv"))
            .with_env_variable("PATH", "/app/.venv/bin:${PATH}", expand=True)
            .with_entrypoint(["/app/.venv/bin/python", "-m", "ibidem_api"])
        )

    @function
    async def publish(
            self, source: dagger.Directory, image: str = "ttl.sh/mortenlj-ibidem-api", version: str = DEVELOP_VERSION
    ) -> list[str]:
        """Publish the application container after building and testing it on-the-fly"""
        platforms = [
            dagger.Platform("linux/amd64"),  # a.k.a. x86_64
            dagger.Platform("linux/arm64"),  # a.k.a. aarch64
        ]
        cos = []
        manifest = dag.container()
        for v in ["latest", version]:
            variants = []
            for platform in platforms:
                variants.append(self.docker(source, platform, version))
            cos.append(manifest.publish(f"{image}:{v}", platform_variants=variants))

        return await asyncio.gather(*cos)

    @function
    async def assemble_manifests(
            self, source: dagger.Directory, image: str = "ttl.sh/mortenlj-ibidem-api", version: str = DEVELOP_VERSION
    ) -> dagger.File:
        """Assemble manifests"""
        template_dir = source.directory("deploy")
        documents = []
        for filepath in await template_dir.entries():
            src = await template_dir.file(filepath).contents()
            if not filepath.endswith(".j2"):
                contents = src
            else:
                template = Template(src, enable_async=True)
                contents = await template.render_async(image=image, version=version)
            if contents.startswith("---"):
                documents.append(contents)
            else:
                documents.append("---\n" + contents)
        return await source.with_new_file("deploy.yaml", "\n".join(documents)).file("deploy.yaml")
