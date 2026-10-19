from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator


Tipo = Literal["pedido", "consulta", "queja"]
Urgencia = Literal["baja", "media", "alta"]
EstadoSolicitud = Literal["pendiente", "en_proceso", "resuelta"]


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tipo: Tipo
    producto: StrictStr | None
    cantidad: StrictInt | None
    urgencia: Urgencia
    resumen: StrictStr = Field(min_length=1, max_length=300)

    @field_validator("producto")
    @classmethod
    def product_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("producto debe ser texto no vacío o null")
        return value

    @field_validator("cantidad")
    @classmethod
    def positive_quantity(cls, value):
        if value is not None and value < 1:
            raise ValueError("cantidad debe ser un entero positivo o null")
        return value

    @model_validator(mode="after")
    def quantity_only_for_orders(self):
        if self.tipo != "pedido" and self.cantidad is not None:
            raise ValueError("cantidad solo aplica a pedidos")
        return self


class SolicitudCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    cliente_id: StrictInt = Field(gt=0)
    producto_id: StrictInt | None = Field(default=None, gt=0)
    tipo: Tipo
    cantidad: StrictInt | None = Field(default=None, gt=0)
    urgencia: Urgencia
    mensaje: StrictStr = Field(min_length=1, max_length=8000)
    recepcion_id: StrictInt | None = Field(default=None, gt=0)
    resumen: StrictStr | None = Field(default=None, max_length=300)
    requiere_revision: bool = False
    motivos_revision: list[StrictStr] = Field(default_factory=list, max_length=12)

    @field_validator("mensaje")
    @classmethod
    def message_not_blank(cls, value):
        if not value.strip():
            raise ValueError("mensaje no puede estar vacío")
        return value

    @model_validator(mode="after")
    def coherent_business_fields(self):
        if self.tipo != "pedido" and self.cantidad is not None:
            raise ValueError("cantidad solo aplica a pedidos")
        if self.tipo == "pedido" and (self.producto_id is None or self.cantidad is None):
            if not self.requiere_revision or not self.motivos_revision:
                raise ValueError("un pedido incompleto requiere revisión y un motivo")
        if self.requiere_revision and not self.motivos_revision:
            raise ValueError("requiere_revision exige al menos un motivo")
        return self


class SolicitudEstadoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: EstadoSolicitud


class ClassificationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: Literal["recibida", "procesando", "registrada", "revision_manual"]
    clasificacion: Classification | None = None
    intentos_llm: StrictInt = Field(ge=0, le=2)
    motivos_revision: list[StrictStr] = Field(default_factory=list, max_length=12)
    ultimo_error: StrictStr | None = Field(default=None, max_length=300)

    @field_validator("ultimo_error")
    @classmethod
    def error_is_safe_code(cls, value):
        if value is None:
            return None
        safe_codes = {
            "invalid_json", "invalid_schema", "llm_unavailable", "llm_not_configured",
            "llm_auth", "llm_error", "api_catalogo_no_disponible", "clasificacion_no_valida",
            "error_clasificacion",
        }
        return value if value in safe_codes else "error_clasificacion"


class ReceptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    cliente_email: StrictStr = Field(min_length=3, max_length=120)
    mensaje: StrictStr = Field(min_length=1, max_length=8000)

    @field_validator("cliente_email")
    @classmethod
    def email_shape(cls, value):
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("cliente_email debe ser un correo válido")
        return value

    @field_validator("mensaje")
    @classmethod
    def message_not_blank(cls, value):
        if not value.strip():
            raise ValueError("mensaje no puede estar vacío")
        return value
