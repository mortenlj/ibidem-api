import base64
from typing import Optional

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_snake


class TokenRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    token: str
    service_account: str
    namespace: str


def to_kebab(s: str) -> str:
    return to_snake(s).replace("_", "-")


class KubeConfigClusterInner(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_kebab))

    certificate_authority_data: Optional[str] = None
    server: str


class KubeConfigCluster(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_kebab))

    cluster: KubeConfigClusterInner
    name: str


class KubeConfigContextInner(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_kebab))

    cluster: str
    namespace: str
    user: str


class KubeConfigContext(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_kebab))

    context: KubeConfigContextInner
    name: str


class KubeConfigUserInner(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_kebab))

    token: str


class KubeConfigUser(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_kebab))

    name: str
    user: KubeConfigUserInner


class KubeConfig(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_kebab))

    api_version: str = "v1"
    kind: str = "Config"
    current_context: str = "default"
    clusters: list[KubeConfigCluster]
    contexts: list[KubeConfigContext]
    users: list[KubeConfigUser]

    @classmethod
    def make(cls, ca_crt, token, server) -> "KubeConfig":
        b64_ca_crt = base64.b64encode(ca_crt).decode("utf-8")
        return cls(
            clusters=[
                KubeConfigCluster(
                    cluster=KubeConfigClusterInner(
                        certificate_authority_data=b64_ca_crt,
                        server=server,
                    ),
                    name="default",
                )
            ],
            contexts=[
                KubeConfigContext(
                    context=KubeConfigContextInner(
                        cluster="default",
                        namespace="default",
                        user="default",
                    ),
                    name="default",
                )
            ],
            users=[
                KubeConfigUser(
                    name="default",
                    user=KubeConfigUserInner(
                        token=token,
                    ),
                )
            ],
        )
