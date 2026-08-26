"""Public catalog: services, programs, stages, modules, topics."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.deps import DbSession
from app.core.enums import ServiceCode
from app.schemas.catalog import (
    ModuleDetailOut,
    ModuleOut,
    ProgramOut,
    ServiceOut,
    ServiceOverviewOut,
    StageOut,
    TopicOut,
)
from app.services import catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/services", response_model=list[ServiceOut])
async def services(db: DbSession) -> list[ServiceOut]:
    return [ServiceOut.model_validate(s) for s in await catalog_service.list_services(db)]


@router.get("/services/{code}", response_model=ServiceOverviewOut)
async def service_overview(code: ServiceCode, db: DbSession) -> ServiceOverviewOut:
    data = await catalog_service.service_overview(db, code)
    return ServiceOverviewOut(
        service=ServiceOut.model_validate(data["service"]),
        programs=[ProgramOut.model_validate(p) for p in data["programs"]],
        stages=[StageOut.model_validate(s) for s in data["stages"]],
        modules=[ModuleOut.model_validate(m) for m in data["modules"]],
    )


@router.get("/stages", response_model=list[StageOut])
async def stages(db: DbSession) -> list[StageOut]:
    return [StageOut.model_validate(s) for s in await catalog_service.list_stages(db)]


@router.get("/programs", response_model=list[ProgramOut])
async def programs(
    db: DbSession, service_id: Annotated[int | None, Query()] = None
) -> list[ProgramOut]:
    rows = await catalog_service.list_programs(db, service_id=service_id)
    return [ProgramOut.model_validate(p) for p in rows]


@router.get("/programs/{slug}", response_model=ProgramOut)
async def program(slug: str, db: DbSession) -> ProgramOut:
    return ProgramOut.model_validate(await catalog_service.get_program(db, slug))


@router.get("/modules", response_model=list[ModuleOut])
async def modules(
    db: DbSession,
    service_id: Annotated[int | None, Query()] = None,
    stage_id: Annotated[int | None, Query()] = None,
) -> list[ModuleOut]:
    rows = await catalog_service.list_modules(db, service_id=service_id, stage_id=stage_id)
    return [ModuleOut.model_validate(m) for m in rows]


@router.get("/modules/{ref}", response_model=ModuleDetailOut)
async def module(ref: str, db: DbSession) -> ModuleDetailOut:
    row = await catalog_service.get_module(db, ref)
    detail = ModuleDetailOut.model_validate(row)
    detail.topics = [
        TopicOut.model_validate(t)
        for t in sorted(row.topics, key=lambda t: (t.sort_order, t.id))
        if t.is_active
    ]
    return detail
