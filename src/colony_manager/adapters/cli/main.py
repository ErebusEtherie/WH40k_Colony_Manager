"""CLI entrypoint for the colony manager prototype."""

from __future__ import annotations

from pathlib import Path

import typer

from colony_manager.adapters.cli.commands.cleanup import cleanup_app
from colony_manager.adapters.config.loader import FileRuleConfigProvider
from colony_manager.adapters.io.colony_exporter import ColonyExporter
from colony_manager.adapters.io.colony_importer import ColonyImporter
from colony_manager.adapters.persistence.colony_repository_impl import SqlAlchemyColonyRepository
from colony_manager.adapters.persistence.db import build_database_url
from colony_manager.adapters.persistence.repositories.colony_user_repository_impl import (
    SqlAlchemyColonyUserRepository,
)
from colony_manager.adapters.persistence.representative_repository_impl import (
    SqlAlchemyRepresentativeRepository,
)
from colony_manager.application.services.colony_service import ColonyService
from colony_manager.application.services.representative_service import RepresentativeService
from colony_manager.domain.enums import (
    ColonyType,
    ModifierCategory,
    RepresentativeType,
    SkillLevel,
)
from colony_manager.domain.errors import ColonyManagerError
from colony_manager.domain.models.colony import Colony
from colony_manager.domain.models.modifier import Modifier
from colony_manager.domain.models.representative import (
    Personality,
    Representative,
    RepresentativeStats,
    Skill,
    Talent,
)

app = typer.Typer(add_completion=False)
colony_app = typer.Typer(help="Colony commands")
representative_app = typer.Typer(help="Representative commands")
app.add_typer(colony_app, name="colony")
app.add_typer(representative_app, name="representative")
app.add_typer(cleanup_app, name="cleanup")


def cli() -> None:
    app()


@app.callback()
def main(
    config_dir: str | None = typer.Option(
        None, "--config-dir", help="Directory containing YAML config files"
    ),
) -> None:
    """Colony manager CLI."""
    global _config_dir
    _config_dir = Path(config_dir or Path(__file__).resolve().parents[3] / "config")
    global _db_path
    _db_path = _config_dir.parent / "colony_manager.sqlite"


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind the API server"),
    port: int = typer.Option(8000, "--port", help="Port to bind the API server"),
) -> None:
    """Start the REST API server."""
    import uvicorn

    from colony_manager.adapters.api.app import create_app

    typer.echo(f"Starting API server on {host}:{port}")
    typer.echo("API docs available at http://localhost:8000/docs")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


@colony_app.command("create")
def create_colony(
    name: str,
    founder_name: str,
    colony_type: str,
    patron_name: str | None = typer.Option(None, "--patron", help="Optional patron (House) name"),
) -> None:
    provider = FileRuleConfigProvider(config_dir=_config_dir)
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    representative_repo = SqlAlchemyRepresentativeRepository(build_database_url(_db_path))
    colony_user_repo = SqlAlchemyColonyUserRepository(build_database_url(_db_path))
    service = ColonyService(colony_repo, representative_repo, provider, colony_user_repo)
    colony_type_config = provider.get_colony_type_config(ColonyType(colony_type))
    base_stats = colony_type_config.base_stats
    colony = Colony(
        name=name,
        founder_name=founder_name,
        patron_name=patron_name,
        colony_type=ColonyType(colony_type),
        age_days=0,
        age_last_updated=__import__("datetime").date.today(),
        base_complacency=base_stats.complacency,
        base_order=base_stats.order,
        base_productivity=base_stats.productivity,
        base_piety=base_stats.piety,
        base_size=base_stats.size,
    )
    created = service.create_colony(colony)
    typer.echo(f"Created colony {created.id}: {created.name}")


@colony_app.command("show")
def show_colony(colony_id: int) -> None:
    provider = FileRuleConfigProvider(config_dir=_config_dir)
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    representative_repo = SqlAlchemyRepresentativeRepository(build_database_url(_db_path))
    colony_user_repo = SqlAlchemyColonyUserRepository(build_database_url(_db_path))
    service = ColonyService(colony_repo, representative_repo, provider, colony_user_repo)
    try:
        state = service.get_state(colony_id)
    except ColonyManagerError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    colony = colony_repo.get(colony_id)
    if colony is None:
        typer.echo(f"Colony {colony_id} not found")
        raise typer.Exit(code=1)

    typer.echo(f"Colony #{colony.id}: {colony.name}")
    typer.echo(f"Founder: {colony.founder_name}")
    if colony.patron_name:
        typer.echo(f"Patron: {colony.patron_name}")
    typer.echo(f"Type: {colony.colony_type}")
    typer.echo(f"Age: {colony.age_days} days")
    typer.echo("State:")
    typer.echo(f"  Size: {state['size']}")
    typer.echo(f"  Complacency: {state['complacency']}")
    typer.echo(f"  Order: {state['order']}")
    typer.echo(f"  Productivity: {state['productivity']}")
    typer.echo(f"  Piety: {state['piety']}")
    typer.echo(f"  Leadership modifier: {state['leadership_modifier']}")
    typer.echo(f"  Profit factor: {state['profit_factor']}")
    typer.echo(f"  Lore state: {state['lore_state']}")


@colony_app.command("list")
def list_colonies() -> None:
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    colonies = colony_repo.list()
    if not colonies:
        typer.echo("No colonies found")
        return

    typer.echo("Colonies:")
    for colony in colonies:
        patron_str = f" | Patron: {colony.patron_name}" if colony.patron_name else ""
        typer.echo(
            f"- #{colony.id}: {colony.name} ({colony.colony_type}) — "
            f"Founder: {colony.founder_name}{patron_str}"
        )


@colony_app.command("set-age")
def set_colony_age(colony_id: int, days: int) -> None:
    """Set the age of a colony in days."""
    provider = FileRuleConfigProvider(config_dir=_config_dir)
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    representative_repo = SqlAlchemyRepresentativeRepository(build_database_url(_db_path))
    colony_user_repo = SqlAlchemyColonyUserRepository(build_database_url(_db_path))
    service = ColonyService(colony_repo, representative_repo, provider, colony_user_repo)
    try:
        updated = service.update_age(colony_id, days)
    except ColonyManagerError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"Set colony {colony_id} age to {updated.age_days} days "
        f"(last updated: {updated.age_last_updated})"
    )


@colony_app.command("add-modifier")
def add_colony_modifier(
    colony_id: int,
    modifier_source_type: str,
    modifier_stat: str,
    modifier_value: int,
    modifier_description: str = typer.Option(
        "", "--description", "-d", help="Description of the modifier"
    ),
) -> None:
    """Add a modifier to a colony."""
    from colony_manager.domain.enums import ModifierSourceType, ModifierStat

    provider = FileRuleConfigProvider(config_dir=_config_dir)
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    representative_repo = SqlAlchemyRepresentativeRepository(build_database_url(_db_path))
    colony_user_repo = SqlAlchemyColonyUserRepository(build_database_url(_db_path))
    service = ColonyService(colony_repo, representative_repo, provider, colony_user_repo)
    try:
        modifier = Modifier(
            colony_id=colony_id,
            modifier_source_type=ModifierSourceType(modifier_source_type),
            modifier_category=ModifierCategory.CUSTOM,
            modifier_stat=ModifierStat(modifier_stat),
            modifier_value=modifier_value,
            modifier_description=modifier_description,
            is_active=True,
        )
        service.add_modifier(colony_id, modifier)
    except ColonyManagerError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"Added modifier to colony {colony_id}: {modifier_description} "
        f"({modifier_stat} {modifier_value:+d})"
    )


@representative_app.command("create")
def create_representative(name: str, representative_type: str) -> None:
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    representative_repo = SqlAlchemyRepresentativeRepository(build_database_url(_db_path))
    service = RepresentativeService(colony_repo, representative_repo)
    representative = Representative(
        name=name,
        type=RepresentativeType(representative_type),
        personalities=[Personality(name="Example", description="desc", stat_effects=[])],
        stats=RepresentativeStats(ws=10, bs=10, s=10, t=10, ag=10, int=10, per=10, wp=10, fel=10),
        skills=[Skill(name="Skill", level=SkillLevel.KNOWN, description="desc")],
        talents=[Talent(name="Talent", description="desc")],
    )
    created = service.create_representative(representative)
    typer.echo(f"Created representative {created.id}: {created.name}")


@representative_app.command("assign")
def assign_representative(colony_id: int, representative_id: int) -> None:
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    representative_repo = SqlAlchemyRepresentativeRepository(build_database_url(_db_path))
    service = RepresentativeService(colony_repo, representative_repo)
    try:
        result = service.assign_to_colony(colony_id, representative_id)
    except ColonyManagerError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    updated = result.representative
    typer.echo(
        f"Assigned representative {representative_id} to colony {colony_id}: "
        f"colony_id={updated.assigned_to_colony_id}"
    )


@colony_app.command("export")
def export_colony(colony_id: int, path: str) -> None:
    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    colony = colony_repo.get(colony_id)
    if colony is None:
        typer.echo(f"Colony {colony_id} not found")
        raise typer.Exit(code=1)
    exporter = ColonyExporter()
    exporter.export(colony=colony, path=path)
    typer.echo(f"Exported colony {colony_id} to {path}")


@colony_app.command("import")
def import_colony(path: str) -> None:
    importer = ColonyImporter()
    import_data = importer.import_from_path(path)
    colony = import_data["colony"]
    representative = import_data["representative"]
    typer.echo(
        f"Imported colony {colony.name} with representative "
        f"{representative.name if representative else 'None'}"
    )


# =============================================================================
# Resource Commands
# =============================================================================


@colony_app.command("add-resource")
def add_resource(
    colony_id: int,
    resource_type: str,
    abundance: int,
    name: str = typer.Option(..., "--name", help="Custom name for this resource deposit"),
    notes: str = typer.Option("", "--notes", help="Optional notes about the resource"),
) -> None:
    """Add a planetary resource to a colony."""
    from colony_manager.adapters.persistence.resource_repository_impl import (
        SqlAlchemyResourceRepository,
    )
    from colony_manager.application.services.resource_service import ResourceService

    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    resource_repo = SqlAlchemyResourceRepository(build_database_url(_db_path))
    service = ResourceService(resource_repo, colony_repo)

    try:
        resource = service.add_resource(
            colony_id=colony_id,
            resource_type=resource_type,
            name=name,
            abundance=abundance,
            notes=notes,
        )
    except ColonyManagerError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Added resource to colony {colony_id}: {resource.name} ({resource.resource_type.value})"
    )
    typer.echo(f"  Abundance: {resource.abundance} ({resource.abundance_level})")
    if resource.notes:
        typer.echo(f"  Notes: {resource.notes}")


@colony_app.command("list-resources")
def list_resources(colony_id: int) -> None:
    """List all planetary resources for a colony."""
    from colony_manager.adapters.persistence.resource_repository_impl import (
        SqlAlchemyResourceRepository,
    )
    from colony_manager.application.services.resource_service import ResourceService

    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    resource_repo = SqlAlchemyResourceRepository(build_database_url(_db_path))
    service = ResourceService(resource_repo, colony_repo)

    # Verify colony exists
    colony = colony_repo.get(colony_id)
    if colony is None:
        typer.echo(f"Colony {colony_id} not found")
        raise typer.Exit(code=1)

    resources = service.list_resources(colony_id)
    if not resources:
        typer.echo(f"Colony {colony_id} has no resources.")
        return

    typer.echo(f"Resources for colony {colony_id} ({colony.name}):")
    typer.echo("-" * 60)
    for resource in resources:
        typer.echo(f"  {resource.name}")
        typer.echo(f"    Type: {resource.resource_type.value}")
        typer.echo(f"    Abundance: {resource.abundance} ({resource.abundance_level})")
        if resource.notes:
            typer.echo(f"    Notes: {resource.notes}")
        typer.echo()


@colony_app.command("update-resource")
def update_resource(
    colony_id: int,
    resource_name: str,
    abundance: int | None = typer.Option(None, "--abundance", help="New abundance value"),
    notes: str | None = typer.Option(None, "--notes", help="New notes (use empty string to clear)"),
) -> None:
    """Update a planetary resource's abundance or notes."""
    from colony_manager.adapters.persistence.resource_repository_impl import (
        SqlAlchemyResourceRepository,
    )
    from colony_manager.application.services.resource_service import ResourceService

    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    resource_repo = SqlAlchemyResourceRepository(build_database_url(_db_path))
    service = ResourceService(resource_repo, colony_repo)

    # Find the resource by name
    resources = service.list_resources(colony_id)
    resource = None
    for r in resources:
        if r.name.lower() == resource_name.lower():
            resource = r
            break

    if resource is None:
        typer.echo(f"Resource '{resource_name}' not found for colony {colony_id}")
        raise typer.Exit(code=1)

    assert resource.id is not None
    if abundance is None and notes is None:
        typer.echo("No changes specified. Use --abundance or --notes to update.")
        raise typer.Exit(code=1)

    try:
        updated = service.update_resource(
            resource_id=resource.id,
            abundance=abundance,
            notes=notes,
        )
    except ColonyManagerError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    typer.echo(f"Updated resource '{updated.name}' for colony {colony_id}:")
    typer.echo(f"  Abundance: {updated.abundance} ({updated.abundance_level})")
    if updated.notes:
        typer.echo(f"  Notes: {updated.notes}")


@colony_app.command("remove-resource")
def remove_resource(colony_id: int, resource_name: str) -> None:
    """Remove a planetary resource from a colony."""
    from colony_manager.adapters.persistence.resource_repository_impl import (
        SqlAlchemyResourceRepository,
    )
    from colony_manager.application.services.resource_service import ResourceService

    colony_repo = SqlAlchemyColonyRepository(build_database_url(_db_path))
    resource_repo = SqlAlchemyResourceRepository(build_database_url(_db_path))
    service = ResourceService(resource_repo, colony_repo)

    # Find the resource by name
    resources = service.list_resources(colony_id)
    resource = None
    for r in resources:
        if r.name.lower() == resource_name.lower():
            resource = r
            break

    if resource is None:
        typer.echo(f"Resource '{resource_name}' not found for colony {colony_id}")
        raise typer.Exit(code=1)

    assert resource.id is not None
    service.remove_resource(resource.id)
    typer.echo(f"Removed resource '{resource.name}' from colony {colony_id}")


_config_dir = Path(__file__).resolve().parents[3] / "config"
_db_path = _config_dir.parent / "colony_manager.sqlite"


if __name__ == "__main__":
    cli()
